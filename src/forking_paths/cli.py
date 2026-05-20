"""Command-line interface for forking-paths."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from forking_paths.classify import classify_turns
from forking_paths.flag import flag_context_sensitive_abandonment
from forking_paths.parser import parse_session
from forking_paths.report import build_report


def _cmd_audit(args: argparse.Namespace) -> int:
    log_path = Path(args.log)
    if not log_path.exists():
        print(f"error: log file not found: {log_path}", file=sys.stderr)
        return 2

    turns = parse_session(log_path)
    census = classify_turns(turns)
    flags = flag_context_sensitive_abandonment(turns, lookback=args.lookback)
    report = build_report(log_path, turns, census, flags)

    out_path = Path(args.out) if args.out else None
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"wrote {out_path} ({len(turns)} turns, {len(flags)} flags)")
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
    a.set_defaults(func=_cmd_audit)

    l = sub.add_parser("list-sessions", help="List session logs in a directory.")
    l.add_argument(
        "--dir",
        default="~/.claude/projects",
        help="Directory to search (default: ~/.claude/projects).",
    )
    l.add_argument("--limit", type=int, default=20, help="Max sessions to list (default: 20).")
    l.set_defaults(func=_cmd_list_sessions)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
