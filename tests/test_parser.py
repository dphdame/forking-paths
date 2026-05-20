from pathlib import Path

from forking_paths.parser import hash_log, parse_session, session_id_from_path

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_clean_session_basic_shape():
    turns = parse_session(FIXTURES / "clean_session.jsonl")
    assert len(turns) == 5
    assert turns[0].role == "user"
    assert turns[1].role == "assistant"
    assert "Loading the data" in turns[1].text
    assert turns[1].tool_uses[0]["name"] == "Bash"


def test_parse_extracts_thinking():
    turns = parse_session(FIXTURES / "directional_prior_with_drop.jsonl")
    thinking_turns = [t for t in turns if t.thinking]
    assert len(thinking_turns) >= 2
    assert any("wrong direction" in t.thinking.lower() for t in thinking_turns)


def test_parse_extracts_tool_uses():
    turns = parse_session(FIXTURES / "considered_not_reported.jsonl")
    bash_calls = [tu for t in turns for tu in t.tool_uses if tu["name"] == "Bash"]
    assert len(bash_calls) == 3
    commands = [tu["input"]["command"] for tu in bash_calls]
    assert "Rscript logit.R" in commands
    assert "Rscript probit.R" in commands


def test_hash_log_deterministic():
    h1 = hash_log(FIXTURES / "clean_session.jsonl")
    h2 = hash_log(FIXTURES / "clean_session.jsonl")
    assert h1 == h2
    assert len(h1) == 64


def test_session_id_from_path():
    assert session_id_from_path("/x/y/abc-def-123.jsonl") == "abc-def-123"
