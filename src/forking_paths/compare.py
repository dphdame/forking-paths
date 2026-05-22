"""Compare a parsed session log against a Prereg.

This module produces a heuristic compliance report. Detection is conservative
and will produce both false positives and false negatives. The README is
explicit about that; this docstring repeats it so callers know what they
are looking at.

The comparison answers four questions:

1. Did the agent run something that looks like the primary specification
   before any other regression-like action?
2. Were any of the locked specifications skipped?
3. Did any ad hoc specifications appear in the log that were not in the
   prereg?
4. When a deviation appears, was a methodological justification written
   into the same response?

v0.3 swaps the keyword-token matcher for sub-estimator fingerprints
extracted from Bash heredoc bodies. The keyword layer remains as a
fallback for assistant prose that names a method but doesn't ship a
heredoc (the prereg side, mostly), and for Rscript-style commands the
fingerprint extractor cannot inspect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

from forking_paths.fingerprint import (
    SpecFingerprint,
    detect_family,
    fingerprint_command,
)
from forking_paths.parser import Turn
from forking_paths.prereg import Prereg


# Regression-like actions: any tool call (Bash, Write) whose command or file
# contains one of these tokens, OR any assistant text that names one of these
# estimators. Used both to detect "the first regression that ran" and to
# enumerate everything that ran.
REGRESSION_KEYWORDS = [
    "regress",
    "ols",
    "logit",
    "probit",
    "lpm",
    "twfe",
    "fixed effect",
    "fixed-effect",
    "did",
    "diff-in-diff",
    "iv",
    "2sls",
    "tsls",
    "liml",
    "jive",
    "rdrobust",
    "rddensity",
    "synth",
    "event study",
    "event-study",
    "callaway",
    "santanna",
    "sant'anna",
    "borusyak",
    "chaisemartin",
    "matching",
    "psm",
    "propensity",
    "lasso",
    "ridge",
    "poisson",
    "negbin",
    "tobit",
]


# Tokens that, if present in a turn that switches methodology, count as a
# methodological reason. Heuristic; an empty match here does not prove no
# justification exists.
JUSTIFICATION_KEYWORDS = [
    "misspec",
    "diagnostic",
    "data quality",
    "identification fail",
    "identification problem",
    "weak instrument",
    "weak first stage",
    "parallel trends",
    "pretrends",
    "pre-trends",
    "negative weight",
    "heterogeneity",
    "selection",
    "endogeneity",
    "missing data",
    "data issue",
    "collinearity",
    "convergence",
    "overdispersion",
    "model misfit",
    "balance fail",
]


# Switch / deviation cues: language that signals the agent changed direction.
SWITCH_KEYWORDS = [
    "let me try a different",
    "let me try another",
    "switch to a",
    "switching to a",
    "let me revise",
    "actually, let me",
    "let me reconsider",
    "different specification",
    "different approach",
    "different estimator",
    "alternative spec",
    "let me run a different",
    "let me use a different",
    "abandon",
    "scrap this",
    "scrap that",
    "discard this approach",
]


# Map from REGRESSION_KEYWORDS tokens to estimator-family strings used by
# the fingerprint layer. Lets us turn a prose-level prereg ladder entry
# ("Callaway-Sant'Anna estimator") into a family identifier that can be
# compared against fingerprints from the session log.
_KEYWORD_TO_FAMILY = {
    "twfe": "DiD-TWFE",
    "fixed effect": "DiD-TWFE",
    "fixed-effect": "DiD-TWFE",
    "diff-in-diff": "DiD-TWFE",
    "did": "DiD-TWFE",
    "callaway": "DiD-CS",
    "santanna": "DiD-CS",
    "sant'anna": "DiD-CS",
    "chaisemartin": "DiD-CS",
    "borusyak": "DiD-CS",
    "event study": "Event-Study",
    "event-study": "Event-Study",
    "iv": "IV-2SLS",
    "2sls": "IV-2SLS",
    "tsls": "IV-2SLS",
    "liml": "IV-LIML",
    "jive": "IV-GMM",
    "rdrobust": "RDD-Local",
    "rddensity": "RDD-Local",
    "synth": "Synthetic-Control-ADH",
    "ols": "OLS",
}


@dataclass
class Deviation:
    """One observed deviation from the prereg.

    v0.3 carries an optional fingerprint reference for the deviating
    specification; v0.2-compatible callers can ignore the field.
    """

    turn_index: int
    what_changed: str
    justification_provided: bool
    justification_text: str = ""
    fingerprint: Optional[SpecFingerprint] = None


@dataclass
class ComparisonReport:
    """Result of comparing a session log to a prereg."""

    primary_spec_ran_first: bool = False
    primary_spec_detected_at_turn: Optional[int] = None
    first_regression_action_turn: Optional[int] = None
    first_regression_action_text: str = ""
    deviations: list[Deviation] = field(default_factory=list)
    ad_hoc_specs: list[str] = field(default_factory=list)
    missed_specs: list[str] = field(default_factory=list)
    verdict: str = "non_compliant"
    prereg_source: str = ""
    # v0.3 additions. Kept additive so the v0.2 public API stays stable.
    observed_fingerprints: list[SpecFingerprint] = field(default_factory=list)
    primary_family: str = ""
    primary_fingerprint_hash: str = ""
    unresolved_variables: list[str] = field(default_factory=list)


def _turn_text_blob(turn: Turn) -> str:
    """Combined searchable text for one turn: thinking + text + tool inputs."""
    parts: list[str] = []
    if turn.text:
        parts.append(turn.text)
    if turn.thinking:
        parts.append(turn.thinking)
    for tu in turn.tool_uses:
        inp = tu.get("input", {})
        if isinstance(inp, dict):
            for v in inp.values():
                if isinstance(v, str):
                    parts.append(v)
    return "\n".join(parts).lower()


def _is_regression_action(turn: Turn) -> tuple[bool, str]:
    """Return (is_regression_action, short_descriptor)."""
    blob = _turn_text_blob(turn)
    for kw in REGRESSION_KEYWORDS:
        if kw in blob:
            return True, kw
    return False, ""


def _canonicalize(s: str) -> str:
    """Normalize for keyword matching: lowercase, strip apostrophes/hyphens/underscores."""
    return (
        s.lower()
        .replace("'", "")
        .replace("’", "")
        .replace("-", "")
        .replace("_", "")
    )


def _spec_tokens(text: str) -> set[str]:
    """Pull regression-keyword tokens from a free-text fragment."""
    if not text:
        return set()
    norm = _canonicalize(text)
    found = set()
    for kw in REGRESSION_KEYWORDS:
        norm_kw = _canonicalize(kw)
        if norm_kw in norm:
            found.add(norm_kw)
    return found


def _spec_fingerprints(turn: Turn) -> list[SpecFingerprint]:
    """Extract fingerprints from every Bash command in a turn."""
    out: list[SpecFingerprint] = []
    for tu in turn.tool_uses:
        if tu.get("name") != "Bash":
            continue
        inp = tu.get("input", {})
        cmd = inp.get("command", "") if isinstance(inp, dict) else ""
        if not cmd:
            continue
        out.extend(fingerprint_command(cmd))
    return out


def _families_from_text(text: str) -> set[str]:
    """Best-effort family guess for free text (used for prereg specs).

    Looks for keyword tokens, maps them to estimator families.
    """
    if not text:
        return set()
    low = _canonicalize(text)
    families: set[str] = set()
    for kw, fam in _KEYWORD_TO_FAMILY.items():
        if _canonicalize(kw) in low:
            families.add(fam)
    return families


def _has_justification(turn: Turn) -> tuple[bool, str]:
    """Detect whether the turn contains a methodological justification."""
    blob = _turn_text_blob(turn)
    for kw in JUSTIFICATION_KEYWORDS:
        if kw in blob:
            idx = blob.find(kw)
            start = max(0, idx - 60)
            end = min(len(blob), idx + len(kw) + 60)
            snippet = blob[start:end].replace("\n", " ")
            return True, snippet
    return False, ""


def _is_switch(turn: Turn) -> bool:
    blob = _turn_text_blob(turn)
    for kw in SWITCH_KEYWORDS:
        if kw in blob:
            return True
    return False


def _fp_short(fp: SpecFingerprint) -> str:
    """Compact human-readable string for one fingerprint."""
    parts = [fp.estimator_family]
    if fp.outcome:
        parts.append(f"y={fp.outcome}")
    if fp.covariates:
        cov = ",".join(fp.covariates[:4])
        if len(fp.covariates) > 4:
            cov += ",..."
        parts.append(f"X=[{cov}]")
    if fp.fe_structure:
        parts.append(f"FE={'+'.join(fp.fe_structure)}")
    if fp.cluster_spec and fp.cluster_spec != "none":
        parts.append(f"cluster={fp.cluster_spec}")
    if fp.sample_restriction:
        parts.append(f"sample={fp.sample_restriction[:40]}")
    return " ".join(parts)


def compare_session_to_prereg(
    turns: list[Turn],
    prereg: Prereg,
) -> ComparisonReport:
    """Cross-check a session log against the prereg.

    Heuristic. Returns a ComparisonReport with deviations, ad hoc
    additions, and missed specs. The verdict synthesizes those.
    """
    report = ComparisonReport(prereg_source=prereg.source_path or "")

    primary_families = _families_from_text(prereg.primary_specification)
    ladder_families: list[set[str]] = [
        _families_from_text(entry) for entry in prereg.robustness_ladder
    ]
    locked_all_families: set[str] = set(primary_families)
    for s in ladder_families:
        locked_all_families |= s

    # Keyword sets stay for backwards compatibility on text-only fixtures.
    primary_tokens = _spec_tokens(prereg.primary_specification)
    locked_ladder_tokens = [
        _spec_tokens(entry) for entry in prereg.robustness_ladder
    ]
    locked_all_tokens: set[str] = set(primary_tokens)
    for s in locked_ladder_tokens:
        locked_all_tokens |= s

    if primary_families:
        report.primary_family = sorted(primary_families)[0]

    observed_tokens: set[str] = set()
    observed_families: set[str] = set()
    primary_seen_first = False
    primary_seen_at: Optional[int] = None
    unresolved: list[str] = []

    for turn in turns:
        if turn.role != "assistant":
            continue

        fingerprints = _spec_fingerprints(turn)
        if fingerprints:
            report.observed_fingerprints.extend(fingerprints)
            for fp in fingerprints:
                observed_families.add(fp.estimator_family)
                if "UNRESOLVED" in fp.covariates:
                    unresolved.append(
                        f"turn {turn.index} ({fp.estimator_family}): "
                        f"covariates list could not be resolved from AST"
                    )

        is_reg, descriptor = _is_regression_action(turn)
        # Treat the fingerprint layer as authoritative only when it can
        # actually identify a family. All-"Unknown" fingerprints (e.g.
        # ``Rscript twfe_primary.R`` -- no heredoc to inspect) fall back
        # to the keyword-token matcher so v0.2-style fixtures still work.
        actionable_fps = [fp for fp in fingerprints if fp.estimator_family != "Unknown"]

        if is_reg and report.first_regression_action_turn is None:
            report.first_regression_action_turn = turn.index
            report.first_regression_action_text = descriptor
            # Prefer fingerprint-family check; fall back to keyword tokens.
            if actionable_fps and primary_families:
                if any(fp.estimator_family in primary_families for fp in actionable_fps):
                    primary_seen_first = True
                    primary_seen_at = turn.index
                    for fp in actionable_fps:
                        if fp.estimator_family in primary_families:
                            report.primary_fingerprint_hash = fp.command_hash
                            break
            else:
                # Keyword path: matches both for Rscript fixtures and the
                # v0.2-compatible mixed case where fingerprint returns Unknown.
                if primary_tokens:
                    turn_tokens = _spec_tokens(_turn_text_blob(turn))
                    if primary_tokens & turn_tokens:
                        primary_seen_first = True
                        primary_seen_at = turn.index

        if is_reg:
            observed_tokens |= _spec_tokens(_turn_text_blob(turn))

        if _is_switch(turn):
            has_just, just_snippet = _has_justification(turn)
            switch_descriptor = descriptor or "specification switch"
            if actionable_fps:
                fp = actionable_fps[0]
                switch_descriptor = f"switched to: {_fp_short(fp)}"
                report.deviations.append(
                    Deviation(
                        turn_index=turn.index,
                        what_changed=switch_descriptor,
                        justification_provided=has_just,
                        justification_text=just_snippet,
                        fingerprint=fp,
                    )
                )
                continue
            new_tokens = _spec_tokens(_turn_text_blob(turn))
            if new_tokens:
                switch_descriptor = (
                    f"switched to: {', '.join(sorted(new_tokens))}"
                )
            report.deviations.append(
                Deviation(
                    turn_index=turn.index,
                    what_changed=switch_descriptor,
                    justification_provided=has_just,
                    justification_text=just_snippet,
                )
            )

    # Detect sub-estimator drift even without a switch-keyword: every
    # observed fingerprint whose hash differs from the locked primary's
    # is a candidate deviation. This is the v0.3-distinct behavior --
    # v0.2 treated three TWFE sub-specs as one drift; v0.3 treats them
    # as three. Skip Unknown-family fingerprints; those flow through the
    # keyword-token path so v0.2-style fixtures behave as before.
    actionable_all = [
        fp for fp in report.observed_fingerprints
        if fp.estimator_family != "Unknown"
    ]
    if actionable_all and primary_families:
        primary_hash = report.primary_fingerprint_hash
        seen_hashes: set[str] = set()
        for fp in actionable_all:
            if not primary_hash and fp.estimator_family in primary_families:
                primary_hash = fp.command_hash
                report.primary_fingerprint_hash = primary_hash
                break
        already_logged: set[str] = {
            d.fingerprint.command_hash
            for d in report.deviations
            if d.fingerprint is not None
        }
        for fp in actionable_all:
            if fp.command_hash == primary_hash:
                seen_hashes.add(fp.command_hash)
                continue
            if fp.command_hash in already_logged or fp.command_hash in seen_hashes:
                continue
            turn_idx = _find_turn_for_fingerprint(turns, fp)
            turn_obj = turns[turn_idx] if 0 <= turn_idx < len(turns) else None
            if turn_obj is not None:
                has_just, just_snippet = _has_justification(turn_obj)
            else:
                has_just, just_snippet = (False, "")
            report.deviations.append(
                Deviation(
                    turn_index=turn_idx,
                    what_changed=f"sub-spec drift: {_fp_short(fp)}",
                    justification_provided=has_just,
                    justification_text=just_snippet,
                    fingerprint=fp,
                )
            )
            seen_hashes.add(fp.command_hash)

    report.primary_spec_ran_first = primary_seen_first
    report.primary_spec_detected_at_turn = primary_seen_at
    report.unresolved_variables = unresolved

    # Ad hoc additions: observed families/tokens not in any locked spec.
    actionable_families = observed_families - {"Unknown"}
    ad_hoc_families = sorted(actionable_families - locked_all_families)
    ad_hoc_keyword = sorted(observed_tokens - locked_all_tokens) if locked_all_tokens else []
    # When the fingerprint layer identified a real family for at least one
    # spec, use families. When everything came through as Unknown (i.e. the
    # v0.2-era Rscript-style fixtures), report keyword tokens.
    if actionable_families:
        report.ad_hoc_specs = ad_hoc_families
    else:
        report.ad_hoc_specs = ad_hoc_keyword

    # Missed specs: locked ladder entries (and primary) whose families
    # never showed up in observed_families. Falls back to tokens when no
    # actionable fingerprints are available.
    missed: list[str] = []
    if actionable_families:
        if primary_families and not (primary_families & observed_families):
            missed.append(
                f"primary specification: {prereg.primary_specification[:80]}"
            )
        for entry, entry_families in zip(prereg.robustness_ladder, ladder_families):
            if entry_families and not (entry_families & observed_families):
                missed.append(entry[:120])
    else:
        if primary_tokens and not (primary_tokens & observed_tokens):
            missed.append(
                f"primary specification: {prereg.primary_specification[:80]}"
            )
        for entry, entry_tokens in zip(prereg.robustness_ladder, locked_ladder_tokens):
            if entry_tokens and not (entry_tokens & observed_tokens):
                missed.append(entry[:120])
    report.missed_specs = missed

    # Verdict.
    if report.deviations and any(
        not d.justification_provided for d in report.deviations
    ):
        report.verdict = "non_compliant"
    elif report.deviations:
        report.verdict = "compliant_with_documented_deviations"
    elif report.missed_specs:
        report.verdict = "non_compliant"
    else:
        report.verdict = "compliant"

    return report


def _find_turn_for_fingerprint(turns: list[Turn], fp: SpecFingerprint) -> int:
    """Locate the turn index that produced this fingerprint, by re-extraction."""
    for turn in turns:
        if turn.role != "assistant":
            continue
        for tu in turn.tool_uses:
            if tu.get("name") != "Bash":
                continue
            inp = tu.get("input", {})
            cmd = inp.get("command", "") if isinstance(inp, dict) else ""
            for cand in fingerprint_command(cmd):
                if cand.command_hash == fp.command_hash:
                    return turn.index
    return -1
