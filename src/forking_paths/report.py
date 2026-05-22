"""Render the provenance appendix as Markdown."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from forking_paths.classify import DecisionCensus, extract_considered_specs
from forking_paths.compare import ComparisonReport
from forking_paths.flag import AbandonmentFlag
from forking_paths.parser import Turn, hash_log, session_id_from_path
from forking_paths.prereg import Prereg


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


def _format_fingerprint_table(comparison: ComparisonReport) -> str:
    """Render a per-fingerprint table for the v0.3 audit section."""
    fps = comparison.observed_fingerprints
    if not fps:
        return "_no regression specifications detected by the fingerprint layer_"
    rows = [
        "| # | Family | Outcome | Covariates | FE | Cluster | Sample restr. | Hash |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, fp in enumerate(fps, 1):
        cov = ", ".join(fp.covariates[:4]) if fp.covariates else "_(none)_"
        if fp.covariates and len(fp.covariates) > 4:
            cov += ", ..."
        fe = "+".join(fp.fe_structure) if fp.fe_structure else "_(none)_"
        clust = fp.cluster_spec or "none"
        samp = (fp.sample_restriction or "_(full)_")[:40]
        rows.append(
            f"| {i} | `{fp.estimator_family}` | `{fp.outcome or '?'}` | "
            f"{cov} | {fe} | {clust} | {samp} | `{fp.command_hash}` |"
        )
    return "\n".join(rows)


def _format_prereg_compliance(
    comparison: ComparisonReport,
    prereg: Prereg,
) -> str:
    """Render the pre-analysis plan compliance section."""
    lines: list[str] = []
    lines.append("## Pre-analysis plan compliance\n")
    lines.append(f"- **Prereg checked:** `{comparison.prereg_source or '(unknown)'}`")
    if prereg.method:
        lines.append(f"- **Method tag:** `{prereg.method}`")
    if comparison.primary_family:
        lines.append(f"- **Primary estimator family (inferred):** `{comparison.primary_family}`")
    lines.append(f"- **Verdict:** **{comparison.verdict}**")

    if comparison.primary_spec_ran_first:
        lines.append(
            f"- Primary specification appears to have run first "
            f"(detected at turn {comparison.primary_spec_detected_at_turn})."
        )
    elif comparison.first_regression_action_turn is not None:
        lines.append(
            f"- First regression-like action at turn "
            f"{comparison.first_regression_action_turn} "
            f"(matched on `{comparison.first_regression_action_text}`) did not "
            "appear to be the locked primary specification."
        )
    else:
        lines.append("- No regression-like actions detected in the session.")

    if prereg.missing_sections:
        lines.append(
            f"- **Prereg sections missing:** {', '.join(prereg.missing_sections)}"
        )
    if prereg.unfilled_sections:
        lines.append(
            f"- **Prereg sections left as placeholder:** "
            f"{', '.join(prereg.unfilled_sections)}"
        )
    lines.append("")

    lines.append("### Deviations\n")
    if comparison.deviations:
        for i, dev in enumerate(comparison.deviations, 1):
            justified = "yes" if dev.justification_provided else "no"
            lines.append(
                f"{i}. Turn {dev.turn_index}: {dev.what_changed} "
                f"(justification documented: **{justified}**)"
            )
            if dev.justification_text:
                lines.append(f"   - Excerpt: _{dev.justification_text}_")
        lines.append("")
    else:
        lines.append("_No specification switches detected in the session._\n")

    lines.append("### Ad hoc additions (in log, not in prereg)\n")
    if comparison.ad_hoc_specs:
        for s in comparison.ad_hoc_specs:
            lines.append(f"- `{s}`")
        lines.append("")
    else:
        lines.append("_None detected._\n")

    lines.append("### Missed specifications (in prereg, not in log)\n")
    if comparison.missed_specs:
        for s in comparison.missed_specs:
            lines.append(f"- {s}")
        lines.append("")
    else:
        lines.append("_None detected._\n")

    lines.append("### Observed sub-estimator fingerprints (v0.3)\n")
    lines.append(_format_fingerprint_table(comparison))
    lines.append("")

    if comparison.unresolved_variables:
        lines.append("### Fingerprinter notes\n")
        lines.append(
            "_The AST fallback could not ground the following variable "
            "references; covariates list shown as `UNRESOLVED`._\n"
        )
        for note in comparison.unresolved_variables[:20]:
            lines.append(f"- {note}")
        lines.append("")

    lines.append(
        "_Compliance detection is heuristic. Fingerprint hashes are computed "
        "over canonicalized (family, outcome, covariates, FE, cluster, sample) "
        "tuples; two specifications with the same hash are treated as the same "
        "sub-estimator. See the limitations section below._\n"
    )

    return "\n".join(lines)


def build_report(
    log_path: str | Path,
    turns: list[Turn],
    census: DecisionCensus,
    flags: list[AbandonmentFlag],
    prereg: Optional[Prereg] = None,
    comparison: Optional[ComparisonReport] = None,
) -> str:
    """Build a Markdown provenance appendix.

    If both ``prereg`` and ``comparison`` are supplied, a pre-analysis plan
    compliance section is inserted after the considered-specifications block.
    """
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

    if prereg is not None and comparison is not None:
        parts.append(_format_prereg_compliance(comparison, prereg))

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
    if prereg is not None:
        parts.append(
            "- Pre-analysis plan compliance is determined by token overlap between "
            "the locked specifications in `prereg.md` and the regression-like actions "
            "in the session log. False positives occur when overlapping estimator "
            "names appear in unrelated contexts. False negatives occur when an "
            "estimator is named in the prereg with synonyms or acronyms not in the "
            "matcher's keyword list."
        )
    parts.append("")
    parts.append("---")
    parts.append(
        "_Generated by [forking-paths](https://github.com/dphdame/forking-paths). "
        "MIT licensed._"
    )

    return "\n".join(parts) + "\n"
