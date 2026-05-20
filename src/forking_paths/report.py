"""Render the provenance appendix as Markdown."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from forking_paths.classify import DecisionCensus, extract_considered_specs
from forking_paths.flag import AbandonmentFlag
from forking_paths.parser import Turn, hash_log, session_id_from_path


def _format_tool_table(counter: Counter) -> str:
    if not counter:
        return "_no tool calls recorded_"
    rows = ["| Tool | Calls |", "|---|---:|"]
    for name, count in counter.most_common():
        rows.append(f"| `{name}` | {count} |")
    return "\n".join(rows)


def _format_flag(flag: AbandonmentFlag, idx: int) -> str:
    return (
        f"### Flag {idx}\n\n"
        f"- **Prior turn:** {flag.prior_turn_index}\n"
        f"- **Abandonment turn:** {flag.abandonment_turn_index} "
        f"(distance: {flag.distance_turns} turns)\n"
        f"- **Prior excerpt:** {flag.prior_excerpt}\n"
        f"- **Abandonment excerpt:** {flag.abandonment_excerpt}\n"
        f"- **Prior pattern matched:** `{flag.matched_prior_pattern}`\n"
        f"- **Abandonment pattern matched:** `{flag.matched_abandonment_pattern}`\n"
    )


def build_report(
    log_path: str | Path,
    turns: list[Turn],
    census: DecisionCensus,
    flags: list[AbandonmentFlag],
) -> str:
    """Build a Markdown provenance appendix."""
    log_path = Path(log_path)
    sha256 = hash_log(log_path)
    session_id = session_id_from_path(log_path)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    considered = extract_considered_specs(turns)

    parts: list[str] = []
    parts.append("# Forking Paths Provenance Report\n")
    parts.append(
        "_A self-audit of decisions taken during an AI-assisted analysis. "
        "Flags are candidates for review, not verdicts._\n"
    )

    parts.append("## Session\n")
    parts.append(f"- **Session ID:** `{session_id}`")
    parts.append(f"- **Log file:** `{log_path.name}`")
    parts.append(f"- **Log SHA-256:** `{sha256}`")
    parts.append(f"- **Report generated:** {generated_at}\n")

    parts.append("## Decision Census\n")
    parts.append(f"- Total turns: **{census.total_turns}**")
    parts.append(f"- User turns: **{census.user_turns}**")
    parts.append(f"- Assistant turns: **{census.assistant_turns}**")
    parts.append(f"- Assistant turns with thinking: **{census.thinking_turns}**")
    parts.append(f"- Specification mentions: **{census.spec_mentions}**")
    parts.append(f"- Sample restriction mentions: **{census.sample_restriction_mentions}**")
    parts.append(
        f"- Variable construction mentions: **{census.variable_construction_mentions}**"
    )
    parts.append(f"- Robustness mentions: **{census.robustness_mentions}**\n")

    parts.append("### Tool calls\n")
    parts.append(_format_tool_table(census.tool_calls_by_type) + "\n")

    if census.bash_commands:
        parts.append("### Bash commands run\n")
        for i, cmd in enumerate(census.bash_commands[:50], 1):
            parts.append(f"{i}. `{cmd}`")
        if len(census.bash_commands) > 50:
            parts.append(f"\n_(truncated: {len(census.bash_commands) - 50} more)_")
        parts.append("")

    if census.file_writes:
        parts.append("### Files written or edited\n")
        unique_files = sorted(set(census.file_writes))
        for f in unique_files[:50]:
            parts.append(f"- `{f}`")
        if len(unique_files) > 50:
            parts.append(f"\n_(truncated: {len(unique_files) - 50} more)_")
        parts.append("")

    parts.append("## Considered Specifications (heuristic)\n")
    if considered:
        for i, spec in enumerate(considered[:30], 1):
            parts.append(f"{i}. {spec}")
        if len(considered) > 30:
            parts.append(f"\n_(truncated: {len(considered) - 30} more)_")
    else:
        parts.append("_No specifications detected by the heuristic._")
    parts.append("")

    parts.append("## Flagged: Context-Sensitive Abandonment\n")
    if flags:
        parts.append(
            f"**{len(flags)} candidate flag(s).** Each represents a directional prior "
            "stated by the user followed by abandonment language from the assistant. "
            "Review each flag and decide whether it warrants explanation in the paper.\n"
        )
        for i, flag in enumerate(flags, 1):
            parts.append(_format_flag(flag, i))
    else:
        parts.append("_No flags raised by the heuristic._\n")

    parts.append("## Limitations\n")
    parts.append(
        "- The flag heuristic is keyword-based and produces both false positives and "
        "false negatives. Treat flags as starting points for self-review."
    )
    parts.append(
        "- The session log can be edited or truncated. The SHA-256 above commits "
        "to the log state at report-generation time only."
    )
    parts.append(
        "- This tool does not detect within-specification p-hacking, garden-of-forking-paths "
        "decisions made outside the agent session, or specifications considered without being run."
    )
    parts.append(
        "- The tool reads decisions visible in the log; it does not evaluate whether the "
        "decisions were correct."
    )
    parts.append("")
    parts.append("---")
    parts.append(
        "_Generated by [forking-paths](https://github.com/dphdame/forking-paths). "
        "MIT licensed._"
    )

    return "\n".join(parts) + "\n"
