# forking-paths

Provenance audit for AI-assisted empirical research. Three layers that together address what happens when reasoning agents help with empirical work and the resulting decision graph needs to be made legible to a referee.

The name is from Andrew Gelman's "garden of forking paths." Every empirical analysis walks past decision points that never appear in the final manuscript. When the research assistant is human, those decisions live in the researcher's head. When the research assistant is an AI agent, the decisions are written down automatically in the session log. The three-layer architecture introduced in v0.2 has been hardened through two follow-on releases: sub-estimator fingerprinting (v0.3) and a structured SPEC-LEDGER contract with a pluggable audit (v1.0). The v1.0 capability section below describes what the audit reads.

## The three layers

**Rule layer.** A universal system prompt the researcher loads at session start. Tells the agent: treat stated priors as hypotheses to test, run the locked primary specification first, do not silently abandon a spec, report all attempted specs. Necessary, and insufficient on its own. Lives at `guardrails/system-prompt.md`.

**Gate layer.** A pre-registration template the agent commits to before running analysis. The agent must run the locked primary specification first. Any deviation requires a written methodological justification in plain text. Universal blank template lives at `guardrails/prereg.template.md`. Method-specific starters for difference-in-differences, regression discontinuity, and instrumental variables live at `guardrails/methods/`. Each method template pre-populates the procedural commitments that current canonical practice locks before estimation, with citations to the methodological literature each one draws on.

**Verification layer.** The audit. Reads the Claude Code session JSONL, cross-checks against the prereg, produces a markdown provenance appendix the researcher can attach to a working paper. v0.1 shipped the audit; v0.2 extended it with the pre-analysis plan compliance section; v0.3 adds sub-estimator specification fingerprinting (see below).

## Install

```bash
git clone https://github.com/dphdame/forking-paths.git
cd forking-paths
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Quick start

```bash
# In a fresh analysis project directory:
forking-paths init --method did

# This drops two files into the current directory:
#   - system-prompt.md     (paste into your Claude Code session at start)
#   - prereg.did.md        (rename to prereg.md and fill in every [fill in])

# After your analysis session:
forking-paths audit ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl \
    --prereg prereg.md \
    --out provenance.md
```

The audit produces a markdown report containing:

- Session metadata (session ID, SHA-256 of the log file, generation timestamp). The hash commits to the log state at audit time.
- Decision census (turn counts, tool calls by type, bash commands, files written, counts of specification / sample-restriction / variable-construction / robustness mentions).
- Considered specifications (heuristic extraction of phrases like "let me try a logit," "consider a two-way fixed-effect model").
- Pre-analysis plan compliance section (when `--prereg` is supplied): whether the primary spec ran first, every documented and undocumented deviation, ad hoc additions, missed specifications, and a verdict (`compliant`, `compliant_with_documented_deviations`, `non_compliant`).
- Flagged context-sensitive abandonment (directional prior in user turn followed by abandonment language in later assistant turn).
- Explicit limitations section.

Attach `provenance.md` as a supplemental file to a working paper, commit it alongside your replication package, or use it for self-review before submitting. A sample is in [`examples/sample_audit_with_prereg.md`](examples/sample_audit_with_prereg.md); the v0.1-only output without the prereg-compliance section is in [`examples/sample_provenance.md`](examples/sample_provenance.md).

## v0.3: sub-estimator fingerprinting

v0.2 identified regression specifications by matching estimator-family keywords (TWFE, Callaway-Sant'Anna, IV, etc.) against Bash commands and assistant prose. That worked at the family level and missed sub-estimator drift: three TWFE regressions in one heredoc -- same family, different outcome / covariates / sample -- collapsed to one keyword hit. Scott Cunningham's framing of the failure mode ("the agent quietly abandons specifications that point the other way") happens at the sub-estimator level, so the family view missed it.

v0.3 ships a fingerprinter (`src/forking_paths/fingerprint.py`) that parses the heredoc body of each Bash command and emits a `SpecFingerprint` per regression call:

- `estimator_family`: one of `DiD-TWFE`, `DiD-CS`, `Event-Study`, `RDD-Local`, `RDD-Global`, `IV-2SLS`, `IV-LIML`, `IV-GMM`, `OLS`, `Synthetic-Control-ADH`, `Synthetic-Control-Generalized`, or `Unknown`.
- `outcome` (dependent variable name).
- `covariates` (tuple of column names or RHS terms).
- `sample_restriction` (any `df = df[...]` filter applied earlier in the block).
- `fe_structure` (e.g. `(entity, time)` for TWFE).
- `cluster_spec` (cluster variable, "robust", or "none").
- `functional_form` (family-specific: bandwidth/kernel for RDD, instrument list for IV, donor pool for SCM, control_group/aggregation for CS).
- `command_hash`: stable 16-char hash of the canonicalized fingerprint, for deduplication.

Family-specific parsers cover `linearmodels.PanelOLS`, `csdid.ATTgt` + `aggte`, `linearmodels.iv.IV2SLS/IVLIML/IVGMM`, `rdrobust`, `pysyncon.Synth`, `gsynth`, `statsmodels.OLS`. A Python AST fallback resolves variable-referenced covariate lists (e.g. `exog=df[model_cols]` where `model_cols` is assembled earlier in the same heredoc). When the AST cannot ground a reference (dynamic for-loops with f-string appends), the fingerprint records `covariates=("UNRESOLVED",)` rather than silently inventing column names; the audit surfaces the unresolved variable name.

The audit's pre-analysis plan compliance section now includes a per-fingerprint table and treats each distinct fingerprint hash as a separate sub-estimator. A heredoc that runs three TWFE sub-specs back-to-back produces three deviation entries when only one of them is the locked primary, rather than collapsing to a single keyword match.

The CLI surface and the public API of `compare_session_to_prereg(turns, prereg)` are unchanged from v0.2. The `ComparisonReport` dataclass is extended additively (`observed_fingerprints`, `primary_family`, `primary_fingerprint_hash`, `unresolved_variables`); v0.2 callers continue to read the same fields they did before.

## v1.0: SPEC-LEDGER audit + contrary-spec requirement

v0.3 identified specifications structurally. v1.0 adds a structured contract for the agent's own reporting: a declared `SPECS-CANDIDATE` list at the start of analysis, a `SPEC-LEDGER` block at the end with one row per declared spec, and a standardized `HEADLINE: estimate=..., sign=..., spec=...` line. The system prompt (`guardrails/system-prompt.md`) gained two new procedural rules: a SPEC-LEDGER format requirement and a contrary-spec requirement (if any candidate spec would produce a result contradicting the stated directional prior, at least one such spec must be run and reported). The point is to convert silent specification abandonment into a parseable audit artifact.

The audit module (`src/forking_paths/ledger_audit.py`, exported as `forking_paths.audit_session_path`, `audit_session_turns`, `parse_ledger`, `parse_specs_candidate`) consumes the resulting JSONL and emits per-session outcomes:

- `ledger_present`: was a parseable SPEC-LEDGER block produced?
- `unlogged_drops`: count of declared candidate specs absent from the ledger.
- `contrary_run`, `contrary_reported`, `contrary_visible`: did at least one prime-contradicting spec actually execute, and was it reported in the ledger or in final text?
- `contrary_specs_in_ledger`: count of contrary specs listed in the ledger with `ran=yes`.
- `headline_sign`, `headline_estimate`, `headline_correct_sign`.

The audit is task-family-pluggable via a `SpecMenu` (a dataclass of `name`, `classify` function, `all_specs` set, `contrary_specs` subset, and expected `correct_sign`). The default `OVB_MENU` handles the omitted-variable-bias cross-section toy used in v0.4's evaluation; other families plug in their own menus without touching the audit core.

```python
from forking_paths import audit_session_path, OVB_MENU

audit = audit_session_path("trial-001", "G3", "path/to/session.jsonl", menu=OVB_MENU)
print(audit.ledger_present, audit.unlogged_drops, audit.contrary_visible)
```

11 regression tests covering classifier behavior, SPECS-CANDIDATE parsing (with the "skip thinking content" fix), and largest-SPEC-LEDGER-block selection ship in `tests/test_ledger_audit.py`.

## Available methods

| Method | Template | Canonical references |
|---|---|---|
| Difference-in-differences | `guardrails/methods/prereg.did.md` | Callaway & Sant'Anna 2021 JoE; Roth 2022 AER:I; de Chaisemartin & D'Haultfœuille 2020 AER; Borusyak, Jaravel & Spiess 2024 ReStud |
| Regression discontinuity | `guardrails/methods/prereg.rdd.md` | Calonico, Cattaneo & Titiunik 2014 ECMA; Cattaneo, Idrobo & Titiunik 2020 primer; McCrary 2008 JoE; Cattaneo, Jansson & Ma 2020 JASA |
| Instrumental variables | `guardrails/methods/prereg.iv.md` | Stock & Yogo 2005; Montiel Olea & Pflueger 2013 JBES; Andrews, Stock & Sun 2019 ARE |

Each template pre-populates the procedural commitments current canonical practice locks before estimation, plus a clearly marked section for the substantive commitments the researcher fills in. None of the templates take positions on frontier methodological debates. They reflect a snapshot of consensus practice as of May 2026; the README in `guardrails/methods/` invites PRs when the snapshot ages.

## CLI commands

```bash
forking-paths --help                          # Top-level help
forking-paths list-sessions                   # Find Claude Code session logs on disk
forking-paths init [--dir DIR] [--method {did,rdd,iv,none}]
                                              # Drop system prompt + prereg template into a directory
forking-paths audit <log.jsonl> [--prereg prereg.md] [--out report.md] [--lookback N]
                                              # Audit a session log; optionally cross-check against prereg
```

## What this tool is not

- **Not a fraud detector.** Session logs are editable. The SHA-256 commits to the log at the moment the report is generated; a determined bad actor edits and re-hashes. The tool serves honest researchers who want to demonstrate discipline and self-auditors who want to check their own work before submitting.
- **Not a replacement for pre-registration with a registry.** This tool's prereg is a project-local commitment the agent runs against. Submission to OSF, AEA RCT Registry, or a similar venue still belongs in your workflow.
- **Not a p-hacking detector.** It surfaces the decision graph; it does not evaluate whether the decisions were correct.
- **Not a substitute for substantive judgment.** Whether parallel trends are plausible in your context, whether your instrument is exogenous, whether your bandwidth is defensible: these are the researcher's calls. The tool moves the procedural floor up so substantive work can stay where it belongs.
- **Not silent about its heuristic limits.** Compliance detection is keyword-based and produces both false positives and false negatives. Every report ends with a limitations section a referee can read.

## Why this exists

Reasoning models like Claude Code keep a running JSON log of every decision they make on the way to a result. At the May 8, 2026 NBER Applications of AI in Healthcare panel, Scott Cunningham flagged that those logs are "full of specification searching," and that telling a model that the literature finds a particular result appears to make it quietly abandon specifications pointing the other way.

The structural issue is upstream of any one tool. Trained priors are weights from gradient descent across enormous text; rules in a system prompt live in context. Context modifies behavior at the margin without overriding the prior. Asking the agent "do not be steered" via a system prompt is asking weights to override themselves through a few tokens of context. Sharma, Tong, Korbak et al. ("Towards Understanding Sycophancy in Language Models," arXiv:2310.13548, 2023) documented the dynamic across five production assistants: rules reduce sycophantic behavior at the margin and the prior wins on most decisions.

The fix needs three layers. The rule layer says what is wanted. The gate layer makes the wrong default more expensive than the right one through architecture: a locked primary specification, a deviation log, a structured commitment the agent has to produce. The verification layer reads what was actually recorded.

This tool ships all three.

## Format support

- **Claude Code session logs** (JSONL, `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`). Working as of v0.2 (May 2026).
- Codex, Cursor, and other agent log formats: not yet supported. PRs welcome.

## Test

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

61 tests across parser, classify, flag, report, prereg, compare, fingerprint, and integration modules. All green at v0.3.0.

## License

MIT. Use it, fork it, ship variants.

## Citation

If this tool meaningfully shapes how you report an analysis, a footnote pointing to the repo is appreciated and helps adoption.

```
Cholette, V. (2026). forking-paths: Provenance audit for AI-assisted empirical research. v0.3.0. https://github.com/dphdame/forking-paths
```

## Acknowledgments

The JSON-log observation that motivated this tool is Scott Cunningham's, surfaced at the May 8, 2026 NBER panel on AI in healthcare research and discussed in the panel writeup by Cunningham and Simon at [causalinf.substack.com](https://causalinf.substack.com/p/what-a-panel-of-economists-said-about). The framing in terms of forking paths is Andrew Gelman and Eric Loken's. The empirical grounding on why rules lose to priors comes from Sharma, Tong, Korbak et al. at Anthropic. The packaging is the contribution here.
