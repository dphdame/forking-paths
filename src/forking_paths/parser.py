"""Parse a Claude Code session log (JSONL) into structured Turn objects."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass
class Turn:
    """One conversational turn in a session log."""

    index: int
    timestamp: str
    role: str
    text: str = ""
    thinking: str = ""
    tool_uses: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    raw_type: str = ""


def _coerce_text(content) -> tuple[str, str, list[dict], list[dict]]:
    """Pull text, thinking, tool_uses, tool_results out of a content payload.

    Handles both list-of-blocks form and bare-string form.
    """
    if isinstance(content, str):
        return content, "", [], []

    if not isinstance(content, list):
        return "", "", [], []

    texts: list[str] = []
    thinkings: list[str] = []
    tool_uses: list[dict] = []
    tool_results: list[dict] = []

    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type", "")
        if btype == "text":
            texts.append(block.get("text", ""))
        elif btype == "thinking":
            thinkings.append(block.get("thinking", ""))
        elif btype == "tool_use":
            tool_uses.append(
                {
                    "name": block.get("name", ""),
                    "input": block.get("input", {}),
                }
            )
        elif btype == "tool_result":
            tool_results.append(
                {
                    "tool_use_id": block.get("tool_use_id", ""),
                    "content": block.get("content", ""),
                }
            )

    return "\n".join(texts), "\n".join(thinkings), tool_uses, tool_results


def parse_session(log_path: str | Path) -> list[Turn]:
    """Parse a JSONL session log into a list of Turn objects."""
    path = Path(log_path)
    turns: list[Turn] = []
    index = 0

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            raw_type = obj.get("type", "")
            if raw_type not in {"user", "assistant", "attachment", "system"}:
                continue

            timestamp = obj.get("timestamp", "")
            message = obj.get("message", {}) if isinstance(obj.get("message"), dict) else {}
            role = message.get("role", raw_type)
            content = message.get("content", "")

            text, thinking, tool_uses, tool_results = _coerce_text(content)

            turns.append(
                Turn(
                    index=index,
                    timestamp=timestamp,
                    role=role,
                    text=text,
                    thinking=thinking,
                    tool_uses=tool_uses,
                    tool_results=tool_results,
                    raw_type=raw_type,
                )
            )
            index += 1

    return turns


def hash_log(log_path: str | Path) -> str:
    """SHA-256 of the raw log bytes. Used to commit to a specific log state."""
    h = hashlib.sha256()
    path = Path(log_path)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def session_id_from_path(log_path: str | Path) -> str:
    """Pull the session UUID from the file stem."""
    return Path(log_path).stem
