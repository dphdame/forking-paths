"""Parse a pre-analysis plan markdown file into a structured Prereg object.

The parser is heuristic. It looks for section headers (## Research question,
## Primary specification, etc.) and pulls the body text under each. It also
detects whether a section is unfilled, defined as: body empty, body equals only
a placeholder like `[fill in]`, or body consists only of a blockquote marker
wrapping a placeholder.

The parser is intentionally tolerant of extra sections and ordering variation
so researchers can adapt the template. Required sections are listed in
``REQUIRED_SECTIONS``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


REQUIRED_SECTIONS = [
    "research question",
    "unit of observation",
    "primary specification",
    "robustness ladder",
    "what would change the conclusion",
    "stop conditions",
]

PLACEHOLDER_MARKERS = [
    "[fill in",
    "[fill-in",
    "tbd",
    "to be filled",
    "todo",
]

METHOD_TAGS = {"did", "rdd", "iv", "cross-section", "time-series", "descriptive", "other"}

# Heading aliases. Map alternative heading text to the canonical key.
HEADING_ALIASES = {
    "research question": "research question",
    "method": "method",
    "method tag": "method",
    "unit of observation": "unit of observation",
    "sample": "sample",
    "primary outcome": "primary outcome",
    "primary specification": "primary specification",
    "procedural commitments": "procedural commitments",
    "substantive commitments specific to this project": "substantive commitments",
    "substantive commitments": "substantive commitments",
    "robustness ladder": "robustness ladder",
    "pre-committed robustness ladder": "robustness ladder",
    "what would change the conclusion": "what would change the conclusion",
    "stop conditions": "stop conditions",
    "citations": "citations",
}


@dataclass
class Prereg:
    """Structured representation of a pre-analysis plan."""

    research_question: str = ""
    unit_of_observation: str = ""
    primary_specification: str = ""
    robustness_ladder: list[str] = field(default_factory=list)
    falsification_criterion: str = ""
    stop_conditions: str = ""
    method: Optional[str] = None
    source_path: Optional[str] = None
    raw_sections: dict[str, str] = field(default_factory=dict)
    missing_sections: list[str] = field(default_factory=list)
    unfilled_sections: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return not self.missing_sections and not self.unfilled_sections


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _normalize_heading(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[:.,]+$", "", text)
    return text


def _split_sections(md: str) -> list[tuple[int, str, str]]:
    """Split markdown into (level, heading_text, body) tuples.

    Top-level (# Title) becomes the document title and is included as a section
    with the heading "<title>" so we don't lose it.
    """
    lines = md.splitlines()
    sections: list[tuple[int, str, list[str]]] = []
    current: Optional[tuple[int, str, list[str]]] = None
    preamble: list[str] = []

    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            if current is not None:
                sections.append(current)
            elif preamble:
                # Stash any pre-heading content under a synthetic key.
                sections.append((0, "_preamble", preamble))
                preamble = []
            level = len(m.group(1))
            heading = m.group(2)
            current = (level, heading, [])
        else:
            if current is None:
                preamble.append(line)
            else:
                current[2].append(line)

    if current is not None:
        sections.append(current)
    elif preamble:
        sections.append((0, "_preamble", preamble))

    return [(lvl, head, "\n".join(body).strip()) for (lvl, head, body) in sections]


def _is_unfilled(body: str) -> bool:
    """Detect whether a section body is unfilled placeholder content."""
    if not body or not body.strip():
        return True
    stripped = body.strip()
    # Strip blockquote markers (lines starting with `> `)
    blockquote_stripped = re.sub(
        r"^>\s?", "", stripped, flags=re.MULTILINE
    ).strip()
    if not blockquote_stripped:
        return True
    lowered = blockquote_stripped.lower()
    # If the entire non-marker content reduces to a placeholder.
    if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
        # Treat the section as unfilled if a placeholder appears AND no
        # substantive prose otherwise. Heuristic: <= 200 chars and a placeholder.
        if len(blockquote_stripped) <= 250:
            return True
        # Or if every non-empty line contains a placeholder marker.
        nonempty = [
            ln for ln in blockquote_stripped.splitlines() if ln.strip()
        ]
        if nonempty and all(
            any(m in ln.lower() for m in PLACEHOLDER_MARKERS) for ln in nonempty
        ):
            return True
    return False


def _extract_method_tag(body: str) -> Optional[str]:
    """Pull a method tag like `did`, `rdd`, `iv` from a Method section body."""
    if not body:
        return None
    # Look for backtick-quoted tag first.
    m = re.search(r"`([a-z_-]+)`", body, re.IGNORECASE)
    if m:
        candidate = m.group(1).lower()
        if candidate in METHOD_TAGS:
            return candidate
    # Fallback: bare token on its own line or in a blockquote.
    cleaned = re.sub(r"^>\s?", "", body, flags=re.MULTILINE).strip().lower()
    for tag in METHOD_TAGS:
        if re.search(rf"\b{re.escape(tag)}\b", cleaned):
            return tag
    return None


def _parse_robustness_ladder(body: str) -> list[str]:
    """Pull numbered-list entries out of a Robustness ladder section body."""
    if not body:
        return []
    items: list[str] = []
    for line in body.splitlines():
        m = re.match(r"^\s*(?:\d+[.)]|[-*])\s+(.+)$", line)
        if m:
            entry = m.group(1).strip()
            # Skip pure placeholders.
            if any(marker in entry.lower() for marker in PLACEHOLDER_MARKERS):
                continue
            items.append(entry)
    return items


def parse_prereg(prereg_path: str | Path) -> Prereg:
    """Parse a pre-analysis plan markdown file into a Prereg object."""
    path = Path(prereg_path)
    md = path.read_text(encoding="utf-8")

    sections = _split_sections(md)

    # Build a {canonical_key: body} dict, last-write-wins.
    section_bodies: dict[str, str] = {}
    for _level, heading, body in sections:
        key = HEADING_ALIASES.get(_normalize_heading(heading))
        if key is None:
            continue
        # If already present and the new body is non-empty, append.
        if key in section_bodies and body:
            section_bodies[key] = section_bodies[key] + "\n\n" + body
        else:
            section_bodies.setdefault(key, body)

    prereg = Prereg(source_path=str(path))
    prereg.raw_sections = dict(section_bodies)

    prereg.research_question = section_bodies.get("research question", "").strip()
    prereg.unit_of_observation = section_bodies.get("unit of observation", "").strip()
    prereg.primary_specification = section_bodies.get(
        "primary specification", ""
    ).strip()
    prereg.falsification_criterion = section_bodies.get(
        "what would change the conclusion", ""
    ).strip()
    prereg.stop_conditions = section_bodies.get("stop conditions", "").strip()
    prereg.robustness_ladder = _parse_robustness_ladder(
        section_bodies.get("robustness ladder", "")
    )

    method_body = section_bodies.get("method", "")
    prereg.method = _extract_method_tag(method_body)

    # Missing vs unfilled.
    for required in REQUIRED_SECTIONS:
        if required not in section_bodies:
            prereg.missing_sections.append(required)
        elif _is_unfilled(section_bodies[required]):
            prereg.unfilled_sections.append(required)

    return prereg
