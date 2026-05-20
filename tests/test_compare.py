from pathlib import Path

from forking_paths.compare import compare_session_to_prereg
from forking_paths.parser import parse_session
from forking_paths.prereg import parse_prereg

FIXTURES = Path(__file__).parent / "fixtures"


def _compare(session_name: str, prereg_name: str = "prereg_clean.md"):
    turns = parse_session(FIXTURES / session_name)
    prereg = parse_prereg(FIXTURES / prereg_name)
    return compare_session_to_prereg(turns, prereg)


def test_followed_prereg_is_compliant():
    report = _compare("session_followed_prereg.jsonl")
    assert report.verdict == "compliant"
    assert report.deviations == []
    assert report.ad_hoc_specs == []
    assert report.primary_spec_ran_first is True
    assert report.primary_spec_detected_at_turn is not None


def test_followed_prereg_primary_detected_before_ladder():
    report = _compare("session_followed_prereg.jsonl")
    # Primary should be detected at the first regression action.
    assert report.primary_spec_detected_at_turn == report.first_regression_action_turn


def test_undocumented_deviation_is_non_compliant():
    report = _compare("session_deviated_from_prereg.jsonl")
    assert report.verdict == "non_compliant"
    assert len(report.deviations) >= 1
    # At least one deviation lacks documented justification.
    assert any(not d.justification_provided for d in report.deviations)


def test_undocumented_deviation_flags_ad_hoc_synth():
    report = _compare("session_deviated_from_prereg.jsonl")
    # `synth_check.R` was run; "synth" is a regression keyword.
    assert "synth" in report.ad_hoc_specs


def test_documented_deviation_records_justification():
    report = _compare("session_documented_deviation.jsonl")
    assert len(report.deviations) >= 1
    # At least one deviation has a documented justification.
    assert any(d.justification_provided for d in report.deviations)
    # And the verdict reflects documented-only deviations.
    assert report.verdict == "compliant_with_documented_deviations"


def test_documented_deviation_justification_text_populated():
    report = _compare("session_documented_deviation.jsonl")
    justified = [d for d in report.deviations if d.justification_provided]
    assert justified
    # The justification snippet should mention a methodological reason.
    snippet_blob = " ".join(d.justification_text.lower() for d in justified)
    assert any(
        kw in snippet_blob
        for kw in ("data quality", "weak instrument", "weak first stage", "misspec", "diagnostic")
    )


def test_prereg_source_path_recorded_on_report():
    report = _compare("session_followed_prereg.jsonl")
    assert "prereg_clean.md" in report.prereg_source
