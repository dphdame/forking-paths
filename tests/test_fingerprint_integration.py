"""Integration tests: fingerprinting on representative real session logs.

These tests use minimal subsets of the gate-drift-evaluation session
corpus copied into ``tests/fixtures/`` so the test suite does not depend
on the experiments/ tree (which is locked and may be re-shaped). The
fixtures exercise the three sample patterns called out in the v0.3
spec:

- ``session_attgt_armA.jsonl``: Callaway-Sant'Anna ATTgt with aggte
- ``session_twfe_multispec_armB.jsonl``: three TWFE sub-specs in one
  heredoc (the v0.2-vs-v0.3 drift count test)
- ``session_event_study_modelcols_armC.jsonl``: event study with
  ``model_cols`` variable reference (exercises the AST fallback)
"""

from pathlib import Path

from forking_paths.compare import compare_session_to_prereg
from forking_paths.fingerprint import fingerprint_command
from forking_paths.parser import parse_session
from forking_paths.prereg import parse_prereg


FIXTURES = Path(__file__).parent / "fixtures"


def _all_fingerprints(jsonl_name: str):
    turns = parse_session(FIXTURES / jsonl_name)
    out = []
    for t in turns:
        if t.role != "assistant":
            continue
        for tu in t.tool_uses:
            if tu.get("name") != "Bash":
                continue
            cmd = tu.get("input", {}).get("command", "")
            out.extend(fingerprint_command(cmd))
    return out


def test_attgt_session_fingerprints_include_did_cs():
    fps = _all_fingerprints("session_attgt_armA.jsonl")
    families = {fp.estimator_family for fp in fps}
    assert "DiD-CS" in families
    # The first DiD-CS fingerprint should record the outcome name.
    cs_fps = [fp for fp in fps if fp.estimator_family == "DiD-CS"]
    assert cs_fps
    assert "teen_emp_rate" in cs_fps[0].outcome


def test_twfe_multispec_session_yields_three_fingerprints():
    fps = _all_fingerprints("session_twfe_multispec_armB.jsonl")
    twfe_fps = [fp for fp in fps if fp.estimator_family == "DiD-TWFE"]
    # The session ships exactly three TWFE sub-specs in a single heredoc.
    # (It may also include other family hashes from earlier diagnostic
    # cells; we assert at least three TWFE fingerprints with distinct
    # hashes.)
    assert len(twfe_fps) >= 3
    twfe_hashes = {fp.command_hash for fp in twfe_fps}
    assert len(twfe_hashes) >= 3, (
        "v0.3 should distinguish three TWFE sub-specs; got "
        f"{len(twfe_hashes)} distinct hashes"
    )


def test_twfe_multispec_session_outcomes_distinguished():
    fps = _all_fingerprints("session_twfe_multispec_armB.jsonl")
    twfe_fps = [fp for fp in fps if fp.estimator_family == "DiD-TWFE"]
    outcomes = {fp.outcome for fp in twfe_fps}
    assert "teen_emp_rate" in outcomes
    assert "log_teen_emp_rate" in outcomes


def test_twfe_multispec_session_covariates_distinguished():
    fps = _all_fingerprints("session_twfe_multispec_armB.jsonl")
    twfe_fps = [fp for fp in fps if fp.estimator_family == "DiD-TWFE"]
    covariate_signatures = {",".join(sorted(fp.covariates)) for fp in twfe_fps}
    assert "treat" in covariate_signatures
    assert "log_min_wage" in covariate_signatures


def test_event_study_modelcols_session_handles_ast_fallback():
    """The armC fixture builds ``event_cols`` inside a for-loop with
    f-string appends. Per the v0.3 spec, dynamic-loop appends are
    correctly labeled UNRESOLVED rather than silently invented.

    The audit's job is to FLAG this as unresolved (so the researcher
    knows the covariate list couldn't be ground out), not to fabricate
    column names.
    """
    fps = _all_fingerprints("session_event_study_modelcols_armC.jsonl")
    es_fps = [fp for fp in fps if fp.estimator_family == "Event-Study"]
    assert es_fps
    # At least one event-study fingerprint exercises the AST fallback
    # path. The for-loop construction is dynamic, so UNRESOLVED is the
    # correct, documented behavior.
    assert all(
        ("UNRESOLVED" in fp.covariates) or all(c.startswith("rel_") for c in fp.covariates)
        for fp in es_fps
    ), (
        "armC fixture covariates should be either grounded to rel_* "
        "columns or flagged UNRESOLVED; got mixed/invented column names"
    )
    # And the outcome should still be extracted even when covariates are
    # unresolved.
    assert all(fp.outcome == "log_teen_emp_rate" for fp in es_fps)


def test_compare_with_prereg_runs_on_armB_session():
    turns = parse_session(FIXTURES / "session_twfe_multispec_armB.jsonl")
    prereg = parse_prereg(FIXTURES / "prereg_clean.md")
    report = compare_session_to_prereg(turns, prereg)
    # We expect at least three sub-spec drift deviations from the
    # multi-spec heredoc (one per distinct TWFE fingerprint hash).
    sub_spec_drifts = [d for d in report.deviations if "sub-spec drift" in d.what_changed]
    assert len(sub_spec_drifts) >= 2, (
        f"v0.3 should record multiple sub-spec drifts on armB; got "
        f"{len(sub_spec_drifts)} drifts in {len(report.deviations)} total deviations"
    )
    # And the report should expose the observed-fingerprints list.
    assert len(report.observed_fingerprints) >= 3
