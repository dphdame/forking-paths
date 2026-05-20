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
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

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


@dataclass
class Deviation:
    """One observed deviation from the prereg."""

    turn_index: int
    what_changed: str
    justification_provided: bool
    justification_text: str = ""


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
    """Normalize for keyword matching: lowercase, strip apostrophes/hyphens/underscores.

    Folds variants like ``Sant'Anna``, ``sant_anna``, ``sant-anna``, ``Santanna``
    all to ``santanna`` so set-difference comparisons across prereg and session
    text behave consistently.
    """
    return (
        s.lower()
        .replace("'", "")
        .replace("’", "")  # right single quote
        .replace("-", "")
        .replace("_", "")
    )


def _spec_tokens(text: str) -> set[str]:
    """Pull regression-keyword tokens from a free-text fragment.

    Tokens are returned in canonical form (apostrophes, hyphens, underscores
    stripped). Two text fragments that name the same estimator with cosmetic
    punctuation differences produce the same canonical token.
    """
    if not text:
        return set()
    norm = _canonicalize(text)
    found = set()
    for kw in REGRESSION_KEYWORDS:
        norm_kw = _canonicalize(kw)
        if norm_kw in norm:
            found.add(norm_kw)
    return found


def _has_justification(turn: Turn) -> tuple[bool, str]:
    """Detect whether the turn contains a methodological justification."""
    blob = _turn_text_blob(turn)
    for kw in JUSTIFICATION_KEYWORDS:
        if kw in blob:
            # Pull a short window around the keyword for the report.
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


def _spec_tokens_in_text(text: str) -> set[str]:
    return _spec_tokens(text)


def compare_session_to_prereg(
    turns: list[Turn],
    prereg: Prereg,
) -> ComparisonReport:
    """Cross-check a session log against the prereg.

    Heuristic. Returns a ComparisonReport with deviations, ad hoc
    additions, and missed specs. The verdict synthesizes those.
    """
    report = ComparisonReport(prereg_source=prereg.source_path or "")

    primary_tokens = _spec_tokens(prereg.primary_specification)
    locked_ladder_tokens = [
        _spec_tokens(entry) for entry in prereg.robustness_ladder
    ]
    locked_all_tokens: set[str] = set(primary_tokens)
    for s in locked_ladder_tokens:
        locked_all_tokens |= s

    # Walk turns once. Find:
    # - first regression action (and whether its tokens overlap the primary)
    # - every regression action's token set (for ad-hoc detection)
    # - every switch (candidate deviations)
    observed_tokens: set[str] = set()
    primary_seen_first = False
    primary_seen_at: Optional[int] = None

    for turn in turns:
        if turn.role != "assistant":
            continue
        is_reg, descriptor = _is_regression_action(turn)
        if is_reg and report.first_regression_action_turn is None:
            report.first_regression_action_turn = turn.index
            report.first_regression_action_text = descriptor
            # Does it overlap with the primary spec tokens?
            turn_tokens = _spec_tokens(_turn_text_blob(turn))
            if primary_tokens and (primary_tokens & turn_tokens):
                primary_seen_first = True
                primary_seen_at = turn.index

        if is_reg:
            observed_tokens |= _spec_tokens(_turn_text_blob(turn))

        if _is_switch(turn):
            has_just, just_snippet = _has_justification(turn)
            switch_descriptor = descriptor or "specification switch"
            # Try to extract the new method tokens from this turn.
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

    # Primary-first detection. If we never saw a regression action at all,
    # primary_spec_ran_first stays False.
    report.primary_spec_ran_first = primary_seen_first
    report.primary_spec_detected_at_turn = primary_seen_at

    # Ad hoc additions: observed tokens not in any locked spec.
    if locked_all_tokens:
        ad_hoc = observed_tokens - locked_all_tokens
        report.ad_hoc_specs = sorted(ad_hoc)
    else:
        report.ad_hoc_specs = []

    # Missed specs: locked ladder entries (and primary) whose tokens never
    # showed up in observed_tokens.
    missed: list[str] = []
    if primary_tokens and not (primary_tokens & observed_tokens):
        missed.append(f"primary specification: {prereg.primary_specification[:80]}")
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
