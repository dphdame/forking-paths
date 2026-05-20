from pathlib import Path

from forking_paths.flag import flag_context_sensitive_abandonment
from forking_paths.parser import parse_session

FIXTURES = Path(__file__).parent / "fixtures"


def test_clean_session_produces_no_flags():
    turns = parse_session(FIXTURES / "clean_session.jsonl")
    flags = flag_context_sensitive_abandonment(turns)
    assert flags == []


def test_directional_prior_with_drop_flags_once():
    turns = parse_session(FIXTURES / "directional_prior_with_drop.jsonl")
    flags = flag_context_sensitive_abandonment(turns)
    assert len(flags) >= 1
    flag = flags[0]
    assert "literature finds" in flag.prior_excerpt.lower()
    assert "wrong direction" in flag.abandonment_excerpt.lower() or "different" in flag.abandonment_excerpt.lower()
    assert flag.distance_turns >= 1


def test_considered_not_reported_does_not_flag():
    turns = parse_session(FIXTURES / "considered_not_reported.jsonl")
    flags = flag_context_sensitive_abandonment(turns)
    assert flags == []
