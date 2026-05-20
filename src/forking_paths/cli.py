"""Command-line interface for forking-paths."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from forking_paths.classify import classify_turns
from forking_paths.compare import compare_session_to_prereg
from forking_paths.flag import flag_context_sensitive_abandonment
from forking_paths.parser import parse_session
from forking_paths.prereg import parse_prereg
from forking_paths.report import build_report


# Method tag -> filename in guardrails/methods/
METHOD_TEMPLATES = {
    "did": "prereg.did.md",
    "rdd": "prereg.rdd.md",
    "iv": "prereg.iv.md",
    "none": None,
}


def _guardrails_dir() -> Path:
    """Locate the installed guardrails/ directory.

    The package is installed editable from the repo root, so guardrails lives
    two parents up from this file (src/forking_paths/cli.py -> repo root).
    """
    here = Path(__file__).resolve()
    # Walk up looking for guardrails/. Editable install: repo_root/guardrails/.
    for parent in here.parents:
        candidate = parent / "guardrails"
        if candidate.is_dir() and (candidate / "system-prompt.md").exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate guardrails/ directory next to the installed package."
    )


def _cmd_audit(args: argparse.Namespace) -> int:
    log_path = Path(args.log)
    if not log_path.exists():
        print(f"error: log file not found: {log_path}", file=sys.stderr)
        return 2

    turns = parse_session(log_path)
    census = classify_turns(turns)
    flags = flag_context_sensitive_abandonment(turns, lookback=args.lookback)

    prereg = None
    comparison = None
    if args.prereg:
        prereg_path = Path(args.prereg)
        if not prereg_path.exists():
            print(f"error: prereg file not found: {prereg_path}", file=sys.stderr)
            return 2
        prereg = parse_prereg(prereg_path)
        comparison = compare_session_to_prereg(turns, prereg)

    report = build_report(
        log_path, turns, census, flags, prereg=prereg, comparison=comparison
    )

    out_path = Path(args.out) if args.out else None
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        suffix = f", verdict={comparison.verdict}" if comparison else ""
        print(
            f"wrote {out_path} ({len(turns)} turns, {len(flags)} flags{suffix})"
        )
    else:
        sys.stdout.write(report)
    return 0


def _cmd_list_sessions(args: argparse.Namespace) -> int:
    base = Path(args.dir).expanduser()
    if not base.exists():
        print(f"error: directory not found: {base}", file=sys.stderr)
        return 2
    sessions = sorted(base.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not sessions:
        print("no .jsonl session files found", file=sys.stderr)
        return 1
    for s in sessions[: args.limit]:
        size_kb = s.stat().st_size // 1024
        print(f"{s}\t{size_kb} KB")
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    target_dir = Path(args.dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        src_dir = _guardrails_dir()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    # Always copy the system prompt.
    sp_src = src_dir / "system-prompt.md"
    sp_dst = target_dir / "system-prompt.md"
    shutil.copyfile(sp_src, sp_dst)

    method = args.method.lower() if args.method else "none"
    template_name = METHOD_TEMPLATES.get(method)
    if template_name is None and method != "none":
        print(
            f"error: unknown --method '{method}'. "
            f"Choose from: {', '.join(k for k in METHOD_TEMPLATES if k != 'none')}, none.",
            file=sys.stderr,
        )
        return 2

    if template_name:
        prereg_src = src_dir / "methods" / template_name
        prereg_dst = target_dir / template_name
    else:
        prereg_src = src_dir / "prereg.template.md"
        prereg_dst = target_dir / "prereg.template.md"

    shutil.copyfile(prereg_src, prereg_dst)

    print(f"Wrote {sp_dst}")
    print(f"Wrote {prereg_dst}")
    print()
    print("Next steps:")
    print(f"  1. Paste {sp_dst.name} into your Claude Code session, or drop into .claude/CLAUDE.md")
    print(f"  2. Rename {prereg_dst.name} to prereg.md and fill in every [fill in] section")
    print(f"  3. After the session: forking-paths audit <log>.jsonl --prereg prereg.md --out provenance.md")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="forking-paths",
        description="Provenance audit for AI-assisted empirical research.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("audit", help="Audit one session log and emit a Markdown report.")
    a.add_argument("log", help="Path to a .jsonl session log.")
    a.add_argument("--out", help="Path to write the Markdown report. Default: stdout.")
    a.add_argument(
        "--lookback",
        type=int,
        default=10,
        help="Max turns between a user prior and assistant abandonment to count as a flag (default: 10).",
    )
    a.add_argument(
        "--prereg",
        help="Optional path to a prereg.md file. When supplied, the report includes a pre-analysis plan compliance section.",
    )
    a.set_defaults(func=_cmd_audit)

    l = sub.add_parser("list-sessions", help="List session logs in a directory.")
    l.add_argument(
        "--dir",
        default="~/.claude/projects",
        help="Directory to search (default: ~/.claude/projects).",
    )
    l.add_argument("--limit", type=int, default=20, help="Max sessions to list (default: 20).")
    l.set_defaults(func=_cmd_list_sessions)

    i = sub.add_parser(
        "init",
        help="Drop the system prompt and a prereg template into a project directory.",
    )
    i.add_argument(
        "--dir",
        default=".",
        help="Target directory (default: current directory).",
    )
    i.add_argument(
        "--method",
        choices=list(METHOD_TEMPLATES.keys()),
        default="none",
        help="Method-specific prereg template to drop. Default: none (universal blank template).",
    )
    i.set_defaults(func=_cmd_init)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
