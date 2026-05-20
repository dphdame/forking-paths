from pathlib import Path

from forking_paths.classify import classify_turns, extract_considered_specs
from forking_paths.parser import parse_session

FIXTURES = Path(__file__).parent / "fixtures"


def test_census_counts_clean_session():
    turns = parse_session(FIXTURES / "clean_session.jsonl")
    census = classify_turns(turns)
    assert census.total_turns == 5
    assert census.user_turns == 2
    assert census.assistant_turns == 3
    assert census.tool_calls_by_type["Bash"] == 2


def test_census_picks_up_spec_mentions():
    turns = parse_session(FIXTURES / "directional_prior_with_drop.jsonl")
    census = classify_turns(turns)
    assert census.spec_mentions > 0


def test_considered_specs_lists_each_model():
    turns = parse_session(FIXTURES / "considered_not_reported.jsonl")
    considered = extract_considered_specs(turns)
    text = " ".join(considered).lower()
    assert "logit" in text
    assert "probit" in text
    assert "linear probability" in text
