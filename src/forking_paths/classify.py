"""Classify turns and build the decision census."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from forking_paths.parser import Turn


SPEC_KEYWORDS = [
    "regression",
    "specification",
    "model",
    "estimate",
    "estimator",
    "ols",
    "logit",
    "probit",
    "did",
    "diff-in-diff",
    "iv",
    "instrument",
    "fixed effect",
    "fixed-effect",
    "synthetic control",
    "panel",
    "event study",
    "rdd",
    "regression discontinuity",
    "propensity",
    "matching",
    "weight",
    "cluster",
    "robust",
]

SAMPLE_RESTRICTION_KEYWORDS = [
    "drop",
    "exclude",
    "filter",
    "restrict",
    "subset",
    "remove",
    "keep only",
]

VARIABLE_KEYWORDS = [
    "code as",
    "define",
    "construct",
    "binary",
    "categorical",
    "log of",
    "log(",
    "winsorize",
    "trim",
]

ROBUSTNESS_KEYWORDS = [
    "robustness",
    "sensitivity",
    "alternative",
    "specification check",
    "placebo",
    "falsification",
]


@dataclass
class DecisionCensus:
    """Aggregate counts of decisions observed in the session."""

    total_turns: int = 0
    user_turns: int = 0
    assistant_turns: int = 0
    thinking_turns: int = 0
    tool_calls_by_type: Counter = field(default_factory=Counter)
    bash_commands: list[str] = field(default_factory=list)
    file_writes: list[str] = field(default_factory=list)
    spec_mentions: int = 0
    sample_restriction_mentions: int = 0
    variable_construction_mentions: int = 0
    robustness_mentions: int = 0


def _contains_any(text: str, keywords: list[str]) -> int:
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def classify_turns(turns: list[Turn]) -> DecisionCensus:
    """Walk the turn list and build a DecisionCensus."""
    census = DecisionCensus(total_turns=len(turns))

    for turn in turns:
        if turn.role == "user":
            census.user_turns += 1
        elif turn.role == "assistant":
            census.assistant_turns += 1
            if turn.thinking:
                census.thinking_turns += 1

        for tu in turn.tool_uses:
            name = tu.get("name", "?")
            census.tool_calls_by_type[name] += 1

            if name == "Bash":
                cmd = tu.get("input", {}).get("command", "")
                if cmd:
                    census.bash_commands.append(cmd[:200])
            elif name in {"Write", "Edit", "MultiEdit"}:
                path = tu.get("input", {}).get("file_path", "")
                if path:
                    census.file_writes.append(path)

        combined = (turn.text or "") + "\n" + (turn.thinking or "")
        census.spec_mentions += _contains_any(combined, SPEC_KEYWORDS)
        census.sample_restriction_mentions += _contains_any(combined, SAMPLE_RESTRICTION_KEYWORDS)
        census.variable_construction_mentions += _contains_any(combined, VARIABLE_KEYWORDS)
        census.robustness_mentions += _contains_any(combined, ROBUSTNESS_KEYWORDS)

    return census


_SPEC_CONSIDERED_RE = re.compile(
    r"(?:let me try|let me run|i'?ll try|i'?ll run|consider|try a|test a) (?:a |an |the )?([^.,\n]{3,80})",
    re.IGNORECASE,
)


def extract_considered_specs(turns: list[Turn]) -> list[str]:
    """Heuristic: pull phrases that look like a specification being considered."""
    seen: list[str] = []
    for turn in turns:
        if turn.role != "assistant":
            continue
        for source in (turn.thinking, turn.text):
            if not source:
                continue
            for match in _SPEC_CONSIDERED_RE.finditer(source):
                phrase = match.group(1).strip()
                if len(phrase) >= 3 and phrase.lower() not in {s.lower() for s in seen}:
                    seen.append(phrase)
    return seen
