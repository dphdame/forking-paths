from pathlib import Path

from forking_paths.classify import classify_turns
from forking_paths.flag import flag_context_sensitive_abandonment
from forking_paths.parser import parse_session
from forking_paths.report import build_report

FIXTURES = Path(__file__).parent / "fixtures"


def test_report_contains_session_id_and_hash():
    log = FIXTURES / "clean_session.jsonl"
    turns = parse_session(log)
    census = classify_turns(turns)
    flags = flag_context_sensitive_abandonment(turns)
    report = build_report(log, turns, census, flags)
    assert "Forking Paths Provenance Report" in report
    assert "clean_session" in report
    assert "SHA-256" in report
    assert "Limitations" in report


def test_report_shows_flag_when_present():
    log = FIXTURES / "directional_prior_with_drop.jsonl"
    turns = parse_session(log)
    census = classify_turns(turns)
    flags = flag_context_sensitive_abandonment(turns)
    report = build_report(log, turns, census, flags)
    assert "Flag 1" in report
    assert "Prior turn" in report


def test_report_handles_zero_flags():
    log = FIXTURES / "clean_session.jsonl"
    turns = parse_session(log)
    census = classify_turns(turns)
    report = build_report(log, turns, census, [])
    assert "No flags raised" in report
