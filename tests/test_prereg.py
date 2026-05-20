from pathlib import Path

import pytest

from forking_paths.prereg import parse_prereg

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_clean_prereg_populates_all_required_fields():
    prereg = parse_prereg(FIXTURES / "prereg_clean.md")
    assert prereg.research_question
    assert "minimum wage" in prereg.research_question.lower()
    assert prereg.unit_of_observation
    assert "county-year" in prereg.unit_of_observation.lower()
    assert prereg.primary_specification
    assert "twfe" in prereg.primary_specification.lower()
    assert prereg.falsification_criterion
    assert prereg.stop_conditions


def test_method_tag_extracted_from_backtick_block():
    prereg = parse_prereg(FIXTURES / "prereg_clean.md")
    assert prereg.method == "did"


def test_robustness_ladder_parses_four_ordered_items():
    prereg = parse_prereg(FIXTURES / "prereg_clean.md")
    assert len(prereg.robustness_ladder) == 4
    # First entry mentions Callaway-Sant'Anna
    assert "callaway" in prereg.robustness_ladder[0].lower()
    # Second mentions event-study
    assert "event-study" in prereg.robustness_ladder[1].lower() or "event study" in prereg.robustness_ladder[1].lower()


def test_clean_prereg_is_complete():
    prereg = parse_prereg(FIXTURES / "prereg_clean.md")
    assert prereg.missing_sections == []
    assert prereg.unfilled_sections == []
    assert prereg.is_complete is True


def test_unfilled_section_detected(tmp_path):
    md = """# Pre-Analysis Plan

## Research question

[fill in]

## Unit of observation

County-year.

## Primary specification

TWFE DiD.

## Robustness ladder

1. Callaway-Sant'Anna.

## What would change the conclusion

Opposite sign.

## Stop conditions

After ladder.
"""
    p = tmp_path / "unfilled.md"
    p.write_text(md, encoding="utf-8")
    prereg = parse_prereg(p)
    assert "research question" in prereg.unfilled_sections
    assert prereg.is_complete is False


def test_missing_section_detected(tmp_path):
    # Drop the "stop conditions" section entirely
    md = """# Pre-Analysis Plan

## Research question

Does X affect Y?

## Unit of observation

County-year.

## Primary specification

TWFE DiD.

## Robustness ladder

1. Callaway-Sant'Anna.

## What would change the conclusion

Opposite sign.
"""
    p = tmp_path / "missing.md"
    p.write_text(md, encoding="utf-8")
    prereg = parse_prereg(p)
    assert "stop conditions" in prereg.missing_sections
    assert prereg.is_complete is False


def test_source_path_recorded():
    prereg = parse_prereg(FIXTURES / "prereg_clean.md")
    assert prereg.source_path is not None
    assert "prereg_clean.md" in prereg.source_path
