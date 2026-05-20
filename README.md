# forking-paths

Provenance audit for AI-assisted empirical research. Three layers that together address what happens when reasoning agents help with empirical work and the resulting decision graph needs to be made legible to a referee.

The name is from Andrew Gelman's "garden of forking paths." Every empirical analysis walks past decision points that never appear in the final manuscript. When the research assistant is human, those decisions live in the researcher's head. When the research assistant is an AI agent, the decisions are written down automatically in the session log. v0.2 ships the architecture to discipline how those decisions get made and the audit that reads what got recorded.

## The three layers

**Rule layer.** A universal system prompt the researcher loads at session start. Tells the agent: treat stated priors as hypotheses to test, run the locked primary specification first, do not silently abandon a spec, report all attempted specs. Necessary, and insufficient on its own. Lives at `guardrails/system-prompt.md`.

**Gate layer.** A pre-registration template the agent commits to before running analysis. The agent must run the locked primary specification first. Any deviation requires a written methodological justification in plain text. Universal blank template lives at `guardrails/prereg.template.md`. Method-specific starters for difference-in-differences, regression discontinuity, and instrumental variables live at `guardrails/methods/`. Each method template pre-populates the procedural commitments that current canonical practice locks before estimation, with citations to the methodological literature each one draws on.

**Verification layer.** The audit. Reads the Claude Code session JSONL, cross-checks against the prereg, produces a markdown provenance appendix the researcher can attach to a working paper. This is what v0.1 shipped; v0.2 extends it with the pre-analysis plan compliance section.

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

28 tests across parser, classify, flag, report, prereg, and compare modules. All green at v0.2.0.

## License

MIT. Use it, fork it, ship variants.

## Citation

If this tool meaningfully shapes how you report an analysis, a footnote pointing to the repo is appreciated and helps adoption.

```
Cholette, V. (2026). forking-paths: Provenance audit for AI-assisted empirical research. v0.2.0. https://github.com/dphdame/forking-paths
```

## Acknowledgments

The JSON-log observation that motivated this tool is Scott Cunningham's, surfaced at the May 8, 2026 NBER panel on AI in healthcare research and discussed in the panel writeup by Cunningham and Simon at [causalinf.substack.com](https://causalinf.substack.com/p/what-a-panel-of-economists-said-about). The framing in terms of forking paths is Andrew Gelman and Eric Loken's. The empirical grounding on why rules lose to priors comes from Sharma, Tong, Korbak et al. at Anthropic. The packaging is the contribution here.
