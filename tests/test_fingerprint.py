"""Tests for the v0.3 sub-estimator fingerprinting layer."""

from pathlib import Path

from forking_paths.fingerprint import (
    SpecFingerprint,
    detect_family,
    extract_heredoc_bodies,
    fingerprint_command,
    fingerprint_one_block,
)


FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Heredoc extraction
# ---------------------------------------------------------------------------

def test_extract_heredoc_body_eof_form():
    cmd = "python3 << 'EOF'\nimport pandas as pd\nprint('hi')\nEOF\n"
    bodies = extract_heredoc_bodies(cmd)
    assert len(bodies) == 1
    assert "print('hi')" in bodies[0]


def test_extract_heredoc_body_dash_form():
    cmd = "python3 - << 'EOF'\nx = 1\nEOF\n"
    bodies = extract_heredoc_bodies(cmd)
    assert len(bodies) == 1
    assert "x = 1" in bodies[0]


def test_extract_returns_command_when_no_heredoc():
    bodies = extract_heredoc_bodies("Rscript foo.R")
    assert bodies == ["Rscript foo.R"]


# ---------------------------------------------------------------------------
# Family detection
# ---------------------------------------------------------------------------

def test_detect_did_twfe():
    body = (
        "from linearmodels.panel import PanelOLS\n"
        "mod = PanelOLS(dependent=df['y'], exog=df[['treat']], "
        "entity_effects=True, time_effects=True)\n"
        "res = mod.fit(cov_type='clustered', clusters=df['state_id'])\n"
    )
    assert detect_family(body) == "DiD-TWFE"


def test_detect_event_study_from_leads_lags():
    body = (
        "from linearmodels.panel import PanelOLS\n"
        "df['rel_time'] = df['year'] - df['gvar']\n"
        "df['rel_neg5'] = (df['rel_time'] == -5).astype(int)\n"
        "df['rel_5'] = (df['rel_time'] == 5).astype(int)\n"
        "mod = PanelOLS(dependent=df['y'], exog=df[['rel_neg5','rel_5']], "
        "entity_effects=True, time_effects=True)\n"
    )
    assert detect_family(body) == "Event-Study"


def test_detect_callaway_santanna():
    body = (
        "from csdid.att_gt import ATTgt\n"
        "cs = ATTgt(yname='y', tname='year', idname='id', gname='g', "
        "data=df, control_group='nevertreated')\n"
    )
    assert detect_family(body) == "DiD-CS"


def test_detect_rdd_local():
    body = "rdrobust(y=df['y'], x=df['running'], c=0, h=0.5, kernel='triangular')"
    assert detect_family(body) == "RDD-Local"


def test_detect_iv_2sls():
    body = (
        "from linearmodels.iv import IV2SLS\n"
        "mod = IV2SLS(dependent=df['y'], exog=df[['x1']], "
        "endog=df[['d']], instruments=df[['z']])\n"
    )
    assert detect_family(body) == "IV-2SLS"


def test_detect_iv_liml():
    body = "mod = IVLIML(dependent=df['y'], exog=df[['x1']], endog=df[['d']], instruments=df[['z']])"
    assert detect_family(body) == "IV-LIML"


def test_detect_synth_adh():
    body = "synth_obj = Synth(treated_unit='CA', donor_pool=['NY','TX'])"
    assert detect_family(body) == "Synthetic-Control-ADH"


def test_detect_synth_generalized():
    body = "out = gsynth(Y='y', D='treat', data=df, estimator='mc')"
    assert detect_family(body) == "Synthetic-Control-Generalized"


def test_detect_unknown_falls_through():
    body = "import pandas as pd\nprint('hello')"
    assert detect_family(body) == "Unknown"


# ---------------------------------------------------------------------------
# Family-specific fingerprint extraction
# ---------------------------------------------------------------------------

def test_twfe_fingerprint_captures_fields():
    body = (
        "from linearmodels.panel import PanelOLS\n"
        "df = df.set_index(['county_id','year'])\n"
        "mod = PanelOLS(dependent=df['teen_emp_rate'], "
        "exog=df[['treat']], entity_effects=True, time_effects=True)\n"
        "res = mod.fit(cov_type='clustered', clusters=df['state_id'])\n"
    )
    fp = fingerprint_one_block(body)
    assert fp is not None
    assert fp.estimator_family == "DiD-TWFE"
    assert fp.outcome == "teen_emp_rate"
    assert fp.covariates == ("treat",)
    assert fp.fe_structure == ("entity", "time")
    assert fp.cluster_spec == "state_id"
    assert len(fp.command_hash) == 16


def test_attgt_fingerprint_captures_cs_kwargs():
    body = (
        "from csdid.att_gt import ATTgt\n"
        "from csdid.aggte_fnc import aggte\n"
        "cs = ATTgt(yname='log_teen_emp_rate', tname='year', "
        "idname='county_id', gname='gvar', data=df, "
        "control_group='nevertreated', anticipation=0, "
        "clustervar='state_id')\n"
        "cs.fit()\n"
        "agg = aggte(cs, type='simple')\n"
    )
    fp = fingerprint_one_block(body)
    assert fp is not None
    assert fp.estimator_family == "DiD-CS"
    assert fp.outcome == "log_teen_emp_rate"
    ff = dict(fp.functional_form)
    assert ff.get("control_group") == "nevertreated"
    assert ff.get("aggregation") == "simple"
    assert fp.cluster_spec == "state_id"


def test_iv_fingerprint_captures_endog_and_instruments():
    body = (
        "from linearmodels.iv import IV2SLS\n"
        "mod = IV2SLS(dependent=df['wage'], exog=df[['educ','age']], "
        "endog=df[['schooling']], instruments=df[['quarter']])\n"
    )
    fp = fingerprint_one_block(body)
    assert fp is not None
    assert fp.estimator_family == "IV-2SLS"
    assert fp.outcome == "wage"
    assert "educ" in fp.covariates
    ff = dict(fp.functional_form)
    assert "schooling" in ff.get("endogenous", "")
    assert "quarter" in ff.get("instruments", "")


def test_rdd_fingerprint_captures_bandwidth_and_kernel():
    body = (
        "out = rdrobust(y=df['outcome'], x=df['score'], c=0.0, "
        "h=0.5, kernel='triangular', p=1)\n"
    )
    fp = fingerprint_one_block(body)
    assert fp is not None
    assert fp.estimator_family == "RDD-Local"
    ff = dict(fp.functional_form)
    assert ff.get("bandwidth") == "0.5"
    assert ff.get("kernel") == "triangular"
    assert ff.get("polynomial_order") == "1"


def test_synth_fingerprint_captures_donor_pool():
    body = (
        "Synth(treated_unit='California', "
        "predictors=df[['gdp_pc','unemp']], "
        "donor_pool=['Texas','NewYork','Florida'])\n"
    )
    fp = fingerprint_one_block(body)
    assert fp is not None
    assert fp.estimator_family == "Synthetic-Control-ADH"
    ff = dict(fp.functional_form)
    assert "Texas" in ff.get("donor_pool", "")


# ---------------------------------------------------------------------------
# Multi-spec heredoc: armB-negative-run01 ships 3 TWFE sub-specs in one block
# ---------------------------------------------------------------------------

def test_three_twfe_subspecs_get_three_fingerprints():
    body = (
        "from linearmodels.panel import PanelOLS\n"
        "df = df.set_index(['county_id','year'])\n"
        "df['log_min_wage'] = np.log(df['min_wage'])\n"
        "\n"
        "mod1 = PanelOLS(dependent=df['teen_emp_rate'], exog=df[['treat']], "
        "entity_effects=True, time_effects=True)\n"
        "res1 = mod1.fit(cov_type='clustered', clusters=df['state_id'])\n"
        "\n"
        "mod2 = PanelOLS(dependent=df['teen_emp_rate'], exog=df[['log_min_wage']], "
        "entity_effects=True, time_effects=True)\n"
        "res2 = mod2.fit(cov_type='clustered', clusters=df['state_id'])\n"
        "\n"
        "mod3 = PanelOLS(dependent=df['log_teen_emp_rate'], exog=df[['treat']], "
        "entity_effects=True, time_effects=True)\n"
        "res3 = mod3.fit(cov_type='clustered', clusters=df['state_id'])\n"
    )
    cmd = f"python3 << 'EOF'\n{body}\nEOF\n"
    fps = fingerprint_command(cmd)
    assert len(fps) == 3
    families = {fp.estimator_family for fp in fps}
    assert families == {"DiD-TWFE"}
    # Three distinct hashes -- v0.2 would have collapsed to one keyword.
    hashes = {fp.command_hash for fp in fps}
    assert len(hashes) == 3
    # Outcomes / covariates differ across sub-specs.
    outcomes = sorted(fp.outcome for fp in fps)
    assert outcomes == ["log_teen_emp_rate", "teen_emp_rate", "teen_emp_rate"]
    cov_signatures = sorted(",".join(fp.covariates) for fp in fps)
    assert cov_signatures == ["log_min_wage", "treat", "treat"]


# ---------------------------------------------------------------------------
# AST fallback: event-study uses model_cols variable reference
# ---------------------------------------------------------------------------

def test_ast_fallback_resolves_model_cols_variable():
    body = (
        "from linearmodels.panel import PanelOLS\n"
        "event_cols = []\n"
        "event_cols.append('rel_neg5')\n"
        "event_cols.append('rel_neg4')\n"
        "event_cols.append('rel_0')\n"
        "event_cols.append('rel_5')\n"
        "model_cols = event_cols\n"
        "df_indexed = df.set_index(['county_id','year'])\n"
        "model = PanelOLS(dependent=df_indexed['log_teen_emp_rate'], "
        "exog=df_indexed[model_cols], entity_effects=True, time_effects=True)\n"
        "result = model.fit(cov_type='clustered', clusters=df_indexed['state_id'])\n"
    )
    fp = fingerprint_one_block(body)
    assert fp is not None
    assert fp.estimator_family == "Event-Study"
    assert fp.outcome == "log_teen_emp_rate"
    # AST fallback should ground model_cols out to event_cols's appended items.
    assert "UNRESOLVED" not in fp.covariates
    assert set(fp.covariates) >= {"rel_neg5", "rel_neg4", "rel_0", "rel_5"}


def test_ast_fallback_marks_unresolvable_dynamic_appends():
    body = (
        "from linearmodels.panel import PanelOLS\n"
        "event_cols = []\n"
        "for r in dynamic_range:\n"
        "    event_cols.append(f'rel_{r}')\n"
        "model = PanelOLS(dependent=df['y'], exog=df[event_cols], "
        "entity_effects=True, time_effects=True)\n"
    )
    fp = fingerprint_one_block(body)
    # We accept either UNRESOLVED in covariates OR an empty covariates set;
    # the contract is "don't silently invent column names".
    assert fp is not None
    # The dynamic for-loop append shouldn't yield ground-truth column names.
    for c in fp.covariates:
        assert not c.startswith("rel_") or c == "UNRESOLVED"


def test_ast_resolves_concat_of_lists():
    body = (
        "from linearmodels.panel import PanelOLS\n"
        "leads = ['rel_neg5','rel_neg4']\n"
        "lags = ['rel_0','rel_1']\n"
        "model_cols = leads + lags\n"
        "mod = PanelOLS(dependent=df['y'], exog=df[model_cols], "
        "entity_effects=True, time_effects=True)\n"
    )
    fp = fingerprint_one_block(body)
    assert fp is not None
    assert set(fp.covariates) == {"rel_neg5", "rel_neg4", "rel_0", "rel_1"}


# ---------------------------------------------------------------------------
# Stable hashing
# ---------------------------------------------------------------------------

def test_same_spec_produces_same_hash():
    body = (
        "PanelOLS(dependent=df['y'], exog=df[['x']], "
        "entity_effects=True, time_effects=True).fit("
        "cov_type='clustered', clusters=df['state'])"
    )
    h1 = fingerprint_one_block(body).command_hash
    h2 = fingerprint_one_block(body).command_hash
    assert h1 == h2


def test_different_outcome_produces_different_hash():
    body_a = (
        "PanelOLS(dependent=df['y_a'], exog=df[['x']], "
        "entity_effects=True, time_effects=True).fit()"
    )
    body_b = (
        "PanelOLS(dependent=df['y_b'], exog=df[['x']], "
        "entity_effects=True, time_effects=True).fit()"
    )
    h_a = fingerprint_one_block(body_a).command_hash
    h_b = fingerprint_one_block(body_b).command_hash
    assert h_a != h_b


def test_different_covariates_produces_different_hash():
    body_a = (
        "PanelOLS(dependent=df['y'], exog=df[['x1']], "
        "entity_effects=True, time_effects=True).fit()"
    )
    body_b = (
        "PanelOLS(dependent=df['y'], exog=df[['x1','x2']], "
        "entity_effects=True, time_effects=True).fit()"
    )
    h_a = fingerprint_one_block(body_a).command_hash
    h_b = fingerprint_one_block(body_b).command_hash
    assert h_a != h_b


# ---------------------------------------------------------------------------
# Whole-command-level fingerprint extraction
# ---------------------------------------------------------------------------

def test_rscript_command_returns_unknown_fingerprint():
    fps = fingerprint_command("Rscript twfe_primary.R")
    # Rscript commands look like regressions but we can't introspect them.
    assert len(fps) == 1
    assert fps[0].estimator_family == "Unknown"


def test_nonregression_command_returns_empty():
    fps = fingerprint_command("ls -la")
    assert fps == []


def test_empty_command_returns_empty():
    assert fingerprint_command("") == []
    assert fingerprint_command(None) == []
