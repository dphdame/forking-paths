"""Specification fingerprinting for AI-generated regression commands.

v0.2 of the audit identified regression specifications via 37 keyword
heuristics at the estimator-family level (TWFE, CS, IV, etc.). That
collapses sub-estimator variants -- same family, different covariates or
sample or functional form -- into one ID. The failure mode flagged by
Scott Cunningham ("the agent quietly abandons specifications that point
the other way") happens at the sub-estimator level, so the keyword view
misses it.

This module extracts a structured ``SpecFingerprint`` from the body of a
Bash ``input.command`` heredoc. The fingerprint is family-aware and
records the substantive choices a researcher would expect a referee to
care about: outcome, covariates, sample restriction, fixed-effects
structure, cluster spec, family-specific kwargs.

The module deliberately uses regex first and Python AST only as a
fallback for variable-referenced covariate / instrument lists. The
heredoc bodies are short Python snippets and the regex layer covers the
common shapes; the AST fallback runs only when the regex layer leaves a
list reference unresolved.

Zero runtime dependencies. Stdlib only.
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional


logger = logging.getLogger(__name__)


ESTIMATOR_FAMILIES = (
    "DiD-TWFE",
    "DiD-CS",
    "Event-Study",
    "RDD-Local",
    "RDD-Global",
    "IV-2SLS",
    "IV-LIML",
    "IV-GMM",
    "OLS",
    "Synthetic-Control-ADH",
    "Synthetic-Control-Generalized",
    "Unknown",
)


@dataclass(frozen=True)
class SpecFingerprint:
    """Structured fingerprint of one regression specification.

    Two fingerprints with the same ``command_hash`` are treated as the
    same sub-estimator. Two fingerprints in the same family that differ
    on any field (outcome, covariates, sample restriction, FE structure,
    cluster, functional form) produce different hashes.
    """

    estimator_family: str
    outcome: str = ""
    covariates: tuple = ()
    sample_restriction: Optional[str] = None
    fe_structure: Optional[tuple] = None
    cluster_spec: str = "none"
    functional_form: tuple = ()
    command_hash: str = ""
    source_excerpt: str = ""

    def to_dict(self) -> dict:
        return {
            "estimator_family": self.estimator_family,
            "outcome": self.outcome,
            "covariates": list(self.covariates),
            "sample_restriction": self.sample_restriction,
            "fe_structure": list(self.fe_structure) if self.fe_structure else None,
            "cluster_spec": self.cluster_spec,
            "functional_form": dict(self.functional_form),
            "command_hash": self.command_hash,
        }


# ---------------------------------------------------------------------------
# Heredoc extraction
# ---------------------------------------------------------------------------

# Match `python3 << 'EOF' ... EOF`, `python3 - << 'EOF' ... EOF`, optional
# quoting and dash variants.
_HEREDOC_RE = re.compile(
    r"<<[-]?\s*['\"]?(?P<delim>[A-Za-z_]\w*)['\"]?\s*\n"
    r"(?P<body>.*?)\n"
    r"(?P=delim)\s*$",
    re.DOTALL | re.MULTILINE,
)


def extract_heredoc_bodies(command: str) -> list[str]:
    """Pull every Python heredoc body out of a shell command string.

    A command like ``python3 << 'EOF' ... EOF`` returns the inner body.
    Commands without a heredoc are returned as a single-element list
    containing the original command (so non-heredoc regression calls
    still flow through the fingerprinter).
    """
    if not command:
        return []
    bodies = [m.group("body") for m in _HEREDOC_RE.finditer(command)]
    if bodies:
        return bodies
    return [command]


# ---------------------------------------------------------------------------
# Family classifiers
# ---------------------------------------------------------------------------

# Each classifier is a (family_label, predicate) pair. The first matching
# predicate wins. Predicates are functions that take the heredoc body and
# return True/False.

_RDROBUST_RE = re.compile(r"\brdrobust\s*\(", re.IGNORECASE)
_RDDENSITY_RE = re.compile(r"\brddensity\s*\(", re.IGNORECASE)
_RDD_GLOBAL_HINT_RE = re.compile(
    r"(?:polynomial|poly\s*\(|\*\*\s*[2-9]|np\.poly1d|polyfit)\s*.*"
    r"(?:running|forcing|score)",
    re.IGNORECASE | re.DOTALL,
)

_ATTGT_RE = re.compile(r"\bATTgt\s*\(", re.IGNORECASE)
_AGGTE_RE = re.compile(r"\baggte\s*\(", re.IGNORECASE)
_CSDID_RE = re.compile(r"\bcsdid\b", re.IGNORECASE)

_PANEL_OLS_RE = re.compile(r"\bPanelOLS\s*\(", re.IGNORECASE)
_LINEARMODELS_RE = re.compile(r"\blinearmodels\b", re.IGNORECASE)

_IV2SLS_RE = re.compile(r"\bIV2SLS\s*\(", re.IGNORECASE)
_IVLIML_RE = re.compile(r"\bIVLIML\s*\(", re.IGNORECASE)
_IVGMM_RE = re.compile(r"\bIVGMM\s*\(", re.IGNORECASE)

_SYNTH_ADH_RE = re.compile(r"\b(?:Synth|pysyncon\.Synth|SCM)\s*\(", re.IGNORECASE)
_SYNTH_GEN_RE = re.compile(r"\b(?:gsynth|GeneralizedSynth|MSCMT)\s*\(", re.IGNORECASE)

_OLS_RE = re.compile(
    r"\b(?:smf\.ols|sm\.OLS|statsmodels.*\bOLS\b|LinearRegression|sklearn.*\.LinearRegression)\s*\(",
    re.IGNORECASE,
)

# Hints that a PanelOLS call is an event study (leads/lags structure).
_EVENT_STUDY_HINT_RE = re.compile(
    r"(?:rel[_]?time|event[_]?time|lead[s]?|lag[s]?|rel_neg\d|rel_\d)",
    re.IGNORECASE,
)


def detect_family(body: str) -> str:
    """Return the estimator family for one heredoc body.

    Predicate order matters: more specific families are checked first.
    """
    if _ATTGT_RE.search(body) or _AGGTE_RE.search(body) or _CSDID_RE.search(body):
        return "DiD-CS"
    if _IV2SLS_RE.search(body):
        return "IV-2SLS"
    if _IVLIML_RE.search(body):
        return "IV-LIML"
    if _IVGMM_RE.search(body):
        return "IV-GMM"
    if _RDROBUST_RE.search(body) or _RDDENSITY_RE.search(body):
        return "RDD-Local"
    if _SYNTH_GEN_RE.search(body):
        return "Synthetic-Control-Generalized"
    if _SYNTH_ADH_RE.search(body):
        return "Synthetic-Control-ADH"
    if _PANEL_OLS_RE.search(body):
        # event-study vs TWFE
        if _EVENT_STUDY_HINT_RE.search(body):
            return "Event-Study"
        return "DiD-TWFE"
    if _RDD_GLOBAL_HINT_RE.search(body):
        return "RDD-Global"
    if _OLS_RE.search(body):
        return "OLS"
    return "Unknown"


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

# Match arg = value form, handling whitespace and trailing commas.
def _kwarg_regex(name: str) -> re.Pattern:
    return re.compile(
        rf"\b{name}\s*=\s*(?P<val>"
        rf"(?:df(?:_\w+)?\[\s*\[[^\]]*\]\s*\])"        # df[['a','b']]
        rf"|(?:df(?:_\w+)?\[\s*'[^']+'\s*\])"          # df['a']
        rf"|(?:df(?:_\w+)?\[\s*\"[^\"]+\"\s*\])"       # df["a"]
        rf"|(?:[A-Za-z_]\w*)"                          # bare var name
        rf"|(?:'[^']*')"                               # 'literal'
        rf"|(?:\"[^\"]*\")"                            # "literal"
        rf"|(?:True|False|None)"
        rf"|(?:-?\d+\.?\d*)"
        rf")",
        re.DOTALL,
    )


def _strip_df_index(expr: str) -> str:
    """``df['x']`` -> ``x``;  ``df[['a','b']]`` -> ``a,b``; ``model_cols`` -> ``model_cols``."""
    if not expr:
        return ""
    m = re.match(r"df(?:_\w+)?\[\s*'([^']+)'\s*\]", expr)
    if m:
        return m.group(1)
    m = re.match(r"df(?:_\w+)?\[\s*\"([^\"]+)\"\s*\]", expr)
    if m:
        return m.group(1)
    m = re.match(r"df(?:_\w+)?\[\s*\[(?P<inner>[^\]]+)\]\s*\]", expr)
    if m:
        items = re.findall(r"['\"]([^'\"]+)['\"]", m.group("inner"))
        if items:
            return ",".join(items)
    if expr.startswith("'") or expr.startswith('"'):
        return expr.strip("'\"")
    return expr


def _extract_kwarg(body: str, name: str) -> str:
    m = _kwarg_regex(name).search(body)
    if not m:
        return ""
    return m.group("val").strip()


def _extract_list_from_kwarg(body: str, name: str) -> tuple:
    """Pull a tuple of column names from a kwarg whose value is a list/df slice.

    Returns ("UNRESOLVED",) and logs the variable name if the value is a
    bare variable reference that the regex layer can't ground.
    """
    raw = _extract_kwarg(body, name)
    if not raw:
        return ()
    # df[['x','y']] form
    if raw.startswith("df"):
        flat = _strip_df_index(raw)
        if flat:
            return tuple(p.strip() for p in flat.split(",") if p.strip())
    # literal list / single col
    if raw.startswith("[") or "," in raw:
        items = re.findall(r"['\"]([^'\"]+)['\"]", raw)
        if items:
            return tuple(items)
    if raw.startswith("'") or raw.startswith('"'):
        return (raw.strip("'\""),)
    # Bare identifier. Try AST resolution.
    resolved = _ast_resolve_variable(body, raw)
    if resolved is not None:
        return tuple(resolved)
    logger.info("Unresolved variable reference for kwarg %s: %s", name, raw)
    return ("UNRESOLVED",)


# ---------------------------------------------------------------------------
# AST fallback for variable-referenced covariate/instrument lists
# ---------------------------------------------------------------------------

def _ast_resolve_variable(body: str, var_name: str) -> Optional[list]:
    """Walk the AST of the heredoc body, find assignments to ``var_name``.

    Resolves the most common patterns we see in agent-generated code:

    - ``model_cols = ['a', 'b']`` -> ['a', 'b']
    - ``model_cols = event_cols`` -> recurse on event_cols
    - ``event_cols = []; event_cols.append('rel_0')`` -> ['rel_0', ...]
    - ``model_cols = leads + lags`` -> concat of resolved lists
    - ``model_cols = [f'rel_{r}' for r in range(...)]`` -> partially
      resolved if range is constant; otherwise label as UNRESOLVED.

    Returns None if resolution fails.
    """
    try:
        tree = ast.parse(body)
    except SyntaxError:
        return None

    # Map of var_name -> value (list or list-of-strings) collected in order.
    assignments: dict[str, list] = {}
    append_calls: dict[str, list] = {}

    def _literal(node) -> Optional[list]:
        if isinstance(node, ast.List):
            out = []
            for el in node.elts:
                if isinstance(el, ast.Constant) and isinstance(el.value, str):
                    out.append(el.value)
                else:
                    return None
            return out
        if isinstance(node, ast.Name) and node.id in assignments:
            return list(assignments[node.id])
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = _literal(node.left)
            right = _literal(node.right)
            if left is not None and right is not None:
                return left + right
            return None
        return None

    for stmt in ast.walk(tree):
        if isinstance(stmt, ast.Assign):
            value_lit = _literal(stmt.value)
            for tgt in stmt.targets:
                if isinstance(tgt, ast.Name) and value_lit is not None:
                    assignments[tgt.id] = value_lit
        elif isinstance(stmt, ast.AugAssign):
            if isinstance(stmt.target, ast.Name):
                value_lit = _literal(stmt.value)
                if value_lit is not None:
                    assignments.setdefault(stmt.target.id, []).extend(value_lit)
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            # Catch x.append('...') / x.append(some_var)
            if (
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "append"
                and isinstance(call.func.value, ast.Name)
                and call.args
            ):
                varname = call.func.value.id
                arg = call.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    append_calls.setdefault(varname, []).append(arg.value)
                # Track that some appends happen even if value is dynamic.
                else:
                    append_calls.setdefault(varname, []).append("UNRESOLVED")

    # Merge appends into assignments (append_calls may also be the sole
    # source if the variable was initialized to [] then appended to).
    for k, items in append_calls.items():
        base = assignments.get(k, [])
        assignments[k] = base + items

    if var_name in assignments:
        resolved = assignments[var_name]
        # If anything inside is UNRESOLVED, propagate that signal.
        if any(x == "UNRESOLVED" for x in resolved):
            return ["UNRESOLVED"]
        return resolved
    return None


# ---------------------------------------------------------------------------
# Per-family parsers
# ---------------------------------------------------------------------------

def _parse_panelols_fields(body: str) -> dict:
    """Extract fields common to PanelOLS-backed families (TWFE, Event-Study)."""
    dep = _extract_kwarg(body, "dependent")
    exog = _extract_kwarg(body, "exog")
    ent_eff = _extract_kwarg(body, "entity_effects").lower() == "true"
    tim_eff = _extract_kwarg(body, "time_effects").lower() == "true"
    fe = []
    if ent_eff:
        fe.append("entity")
    if tim_eff:
        fe.append("time")
    clusters = _extract_kwarg(body, "clusters")
    cluster_spec = _strip_df_index(clusters) if clusters else "none"
    if not cluster_spec:
        cov_type = _extract_kwarg(body, "cov_type")
        if cov_type and "robust" in cov_type.lower():
            cluster_spec = "robust"
        else:
            cluster_spec = "none"
    return {
        "outcome": _strip_df_index(dep),
        "covariates": _extract_list_from_kwarg(body, "exog"),
        "fe_structure": tuple(fe) if fe else None,
        "cluster_spec": cluster_spec,
    }


def _parse_attgt_fields(body: str) -> dict:
    """Extract Callaway-Sant'Anna ATTgt fields."""
    yname = _extract_kwarg(body, "yname").strip("'\"")
    gname = _extract_kwarg(body, "gname").strip("'\"")
    tname = _extract_kwarg(body, "tname").strip("'\"")
    idname = _extract_kwarg(body, "idname").strip("'\"")
    control_group = _extract_kwarg(body, "control_group").strip("'\"")
    anticipation = _extract_kwarg(body, "anticipation")
    clustervar = _extract_kwarg(body, "clustervar").strip("'\"")
    # Aggregation type, if aggte is called in the same body.
    agg_match = re.search(r"aggte\s*\([^,]+,\s*type\s*=\s*['\"]([^'\"]+)['\"]", body)
    agg_type = agg_match.group(1) if agg_match else ""
    return {
        "outcome": yname,
        "covariates": (),  # ATTgt covariates would be xformla; not seen in fixtures
        "functional_form": {
            "gname": gname,
            "tname": tname,
            "idname": idname,
            "control_group": control_group,
            "anticipation": anticipation,
            "aggregation": agg_type,
        },
        "cluster_spec": clustervar or "none",
    }


def _parse_iv_fields(body: str) -> dict:
    """linearmodels IV2SLS / IVLIML / IVGMM kwargs."""
    dep = _extract_kwarg(body, "dependent")
    exog = _extract_kwarg(body, "exog")
    endog = _extract_kwarg(body, "endog")
    instr = _extract_kwarg(body, "instruments")
    clusters = _extract_kwarg(body, "clusters")
    cluster_spec = _strip_df_index(clusters) if clusters else "none"
    return {
        "outcome": _strip_df_index(dep),
        "covariates": _extract_list_from_kwarg(body, "exog"),
        "functional_form": {
            "endogenous": list(_extract_list_from_kwarg(body, "endog")),
            "instruments": list(_extract_list_from_kwarg(body, "instruments")),
        },
        "cluster_spec": cluster_spec,
    }


def _parse_rdrobust_fields(body: str) -> dict:
    """rdrobust(y, x, c=..., h=..., kernel=..., p=...) fields."""
    # rdrobust uses positional or kwarg args; capture common kwargs.
    y = _extract_kwarg(body, "y") or _extract_first_positional(body, "rdrobust", 0)
    x = _extract_kwarg(body, "x") or _extract_first_positional(body, "rdrobust", 1)
    cutoff = _extract_kwarg(body, "c")
    bandwidth = _extract_kwarg(body, "h")
    kernel = _extract_kwarg(body, "kernel").strip("'\"")
    poly = _extract_kwarg(body, "p")
    return {
        "outcome": _strip_df_index(y),
        "covariates": (_strip_df_index(x),) if x else (),
        "functional_form": {
            "cutoff": cutoff,
            "bandwidth": bandwidth,
            "kernel": kernel,
            "polynomial_order": poly,
        },
        "cluster_spec": "none",
    }


def _parse_synth_fields(body: str) -> dict:
    """Synthetic control: donor pool, predictors, treated unit."""
    treated = _extract_kwarg(body, "treated_unit") or _extract_kwarg(body, "treated")
    predictors = _extract_list_from_kwarg(body, "predictors")
    donor = _extract_list_from_kwarg(body, "donor_pool") or _extract_list_from_kwarg(
        body, "control_units"
    )
    outcome = _extract_kwarg(body, "outcome").strip("'\"") or _extract_kwarg(
        body, "yname"
    ).strip("'\"")
    return {
        "outcome": outcome,
        "covariates": predictors,
        "functional_form": {
            "treated_unit": treated.strip("'\""),
            "donor_pool": list(donor),
        },
        "cluster_spec": "none",
    }


def _parse_ols_fields(body: str) -> dict:
    """statsmodels OLS / formula API: outcome ~ x1 + x2."""
    m = re.search(
        r"(?:smf\.ols|formula)\s*\(\s*['\"]([^'\"]+)['\"]", body
    )
    if m:
        formula = m.group(1)
        if "~" in formula:
            lhs, rhs = formula.split("~", 1)
            covariates = tuple(t.strip() for t in re.split(r"\+|\*", rhs) if t.strip())
            return {"outcome": lhs.strip(), "covariates": covariates}
    # sm.OLS(y, X) positional form
    m = re.search(r"sm\.OLS\s*\(\s*([^,]+),\s*([^)]+)\)", body)
    if m:
        return {
            "outcome": _strip_df_index(m.group(1).strip()),
            "covariates": _extract_list_from_kwarg(body, m.group(2).strip())
            or (_strip_df_index(m.group(2).strip()),),
        }
    return {}


def _extract_first_positional(body: str, fn: str, pos: int) -> str:
    """Pull the Nth positional arg from a call to ``fn``.

    Best-effort; only handles simple comma-separated positional args
    without nested calls.
    """
    m = re.search(rf"\b{fn}\s*\(([^)]*)\)", body, re.DOTALL)
    if not m:
        return ""
    args = [a.strip() for a in m.group(1).split(",")]
    # Drop kwarg-shaped args.
    positional = [a for a in args if "=" not in a]
    if pos < len(positional):
        return positional[pos]
    return ""


# ---------------------------------------------------------------------------
# Sample restriction detection
# ---------------------------------------------------------------------------

_SAMPLE_RESTRICTION_RE = re.compile(
    r"df(?:_\w+)?\s*=\s*df(?:_\w+)?\s*\[\s*(?P<expr>df(?:_\w+)?\[[^\]]+\][^\]]*)\s*\]"
)
_FILTER_HINT_RE = re.compile(
    r"(?:\.query\s*\(\s*['\"](?P<q>[^'\"]+)['\"]"
    r"|\.loc\s*\[\s*df(?:_\w+)?\[[^\]]+\]\s*"
    r"|\bdropna\s*\(\s*subset)",
    re.DOTALL,
)


def _detect_sample_restriction(body: str) -> Optional[str]:
    m = _SAMPLE_RESTRICTION_RE.search(body)
    if m:
        return m.group("expr").strip()[:120]
    m = _FILTER_HINT_RE.search(body)
    if m:
        if m.group("q"):
            return f".query({m.group('q')!r})"
        return m.group(0)[:120]
    return None


# ---------------------------------------------------------------------------
# Top-level fingerprint
# ---------------------------------------------------------------------------

def _canonicalize_fields(family: str, fields: dict) -> dict:
    """Lowercase, sort tuples for stable hashing."""
    return {
        "family": family,
        "outcome": fields.get("outcome", ""),
        "covariates": tuple(sorted(fields.get("covariates", ()) or ())),
        "sample_restriction": fields.get("sample_restriction"),
        "fe_structure": tuple(sorted(fields.get("fe_structure", ()) or ()))
        if fields.get("fe_structure")
        else None,
        "cluster_spec": fields.get("cluster_spec", "none"),
        "functional_form": fields.get("functional_form", {}),
    }


def _hash_fields(canon: dict) -> str:
    blob = json.dumps(canon, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def fingerprint_one_block(body: str) -> Optional[SpecFingerprint]:
    """Fingerprint a single regression call inside a heredoc body.

    Returns None if the body has no detectable regression call.
    """
    family = detect_family(body)
    if family == "Unknown" and not _looks_like_regression(body):
        return None

    fields: dict = {}
    if family in ("DiD-TWFE", "Event-Study"):
        fields = _parse_panelols_fields(body)
    elif family == "DiD-CS":
        fields = _parse_attgt_fields(body)
    elif family in ("IV-2SLS", "IV-LIML", "IV-GMM"):
        fields = _parse_iv_fields(body)
    elif family == "RDD-Local":
        fields = _parse_rdrobust_fields(body)
    elif family in ("Synthetic-Control-ADH", "Synthetic-Control-Generalized"):
        fields = _parse_synth_fields(body)
    elif family in ("OLS", "RDD-Global"):
        fields = _parse_ols_fields(body)
    else:
        fields = {}

    fields["sample_restriction"] = _detect_sample_restriction(body)

    # Functional form is dict; freeze to tuple of items for the dataclass.
    ff_dict = fields.get("functional_form", {})
    ff_items = tuple(sorted((k, str(v)) for k, v in (ff_dict.items() if isinstance(ff_dict, dict) else [])))

    canon = _canonicalize_fields(family, fields)
    chash = _hash_fields(canon)

    excerpt = body.strip().splitlines()
    excerpt_text = "\n".join(excerpt[:6])[:400]

    return SpecFingerprint(
        estimator_family=family,
        outcome=fields.get("outcome", "") or "",
        covariates=tuple(fields.get("covariates", ()) or ()),
        sample_restriction=fields.get("sample_restriction"),
        fe_structure=fields.get("fe_structure"),
        cluster_spec=fields.get("cluster_spec", "none"),
        functional_form=ff_items,
        command_hash=chash,
        source_excerpt=excerpt_text,
    )


def _looks_like_regression(body: str) -> bool:
    """Fallback heuristic: does this body look like it ran a regression?"""
    hints = (
        "regress",
        ".fit(",
        "ols(",
        "logit(",
        "probit(",
        "panelols",
        "iv2sls",
        "ivliml",
        "ivgmm",
        "rdrobust",
        "synth(",
        "gsynth(",
        "attgt",
    )
    low = body.lower()
    return any(h in low for h in hints)


_ESTIMATOR_CALL_RE = re.compile(
    r"\b("
    r"PanelOLS|ATTgt|aggte|IV2SLS|IVLIML|IVGMM|rdrobust|rddensity|"
    r"Synth|gsynth|MSCMT|sm\.OLS|smf\.ols|sm\.GLM|LinearRegression"
    r")\s*\(",
    re.IGNORECASE,
)


def _split_into_estimator_blocks(body: str) -> list[str]:
    """Split a heredoc body around each estimator construction.

    One heredoc may run multiple sub-specs back-to-back (e.g.
    armB-negative-run01 ships three TWFE calls in one block). Each call
    is treated as its own fingerprint. We split on estimator-constructor
    boundaries, including the preceding kwargs/exog setup as part of
    each block by greedy-match between consecutive constructors.
    """
    matches = list(_ESTIMATOR_CALL_RE.finditer(body))
    if not matches:
        return [body]
    if len(matches) == 1:
        return [body]
    # Anchor blocks at each constructor; the block runs from the previous
    # boundary up through the next constructor's region (so kwargs assigned
    # immediately before the call stay with that call).
    blocks: list[str] = []
    boundaries = [0] + [m.start() for m in matches[1:]] + [len(body)]
    for i in range(len(matches)):
        start = boundaries[i]
        end = boundaries[i + 1]
        blocks.append(body[start:end])
    return blocks


def fingerprint_command(command: str) -> list[SpecFingerprint]:
    """Fingerprint every regression call in a Bash command string.

    Handles:
      - Plain ``Rscript foo.R`` style commands (returns Unknown family
        with the command as source_excerpt if it looks like a regression
        action).
      - Python heredocs with one or more regression calls.
      - Multi-spec heredocs (split on estimator constructor boundaries).
    """
    if not command:
        return []
    bodies = extract_heredoc_bodies(command)
    out: list[SpecFingerprint] = []
    for body in bodies:
        for block in _split_into_estimator_blocks(body):
            fp = fingerprint_one_block(block)
            if fp is not None:
                out.append(fp)
    # If we got nothing but the command itself mentions a regression
    # token, emit a single Unknown fingerprint so the audit at least
    # records that something ran.
    if not out and _looks_like_regression(command):
        canon = _canonicalize_fields("Unknown", {})
        out.append(
            SpecFingerprint(
                estimator_family="Unknown",
                command_hash=_hash_fields(canon),
                source_excerpt=command[:400],
            )
        )
    return out
