# forking-paths

Provenance audit for AI-assisted empirical research. Reads a Claude Code session log and produces a Markdown report a researcher can attach to a working paper or use for self-review.

The name is from Andrew Gelman's "garden of forking paths." Every empirical analysis walks past decision points that never appear in the final manuscript. When a research assistant is human, those decisions live in the researcher's head. When the research assistant is an AI agent, the decisions are written down automatically in the session log. This tool surfaces them.

## What it does

For one session log, the audit produces:

- **Session metadata.** Session ID, SHA-256 of the log file, generation timestamp. The hash commits to the log state at audit time.
- **Decision census.** Turn counts, tool calls by type, bash commands run, files written or edited, count of specification / sample-restriction / variable-construction / robustness mentions.
- **Considered specifications.** Heuristic extraction of phrases like "let me try a logit," "let me run a probit," "consider a two-way fixed-effect model."
- **Flagged context-sensitive abandonment.** Pairs where a directional prior appears in a user turn ("the literature finds negative employment effects") followed by abandonment language in a later assistant turn ("the result was the wrong direction, let me try a different specification").
- **Limitations.** Explicit, in the report itself, so a referee reading the appendix knows what the heuristic can and cannot see.

A sample report from one of the test fixtures is in [`examples/sample_provenance.md`](examples/sample_provenance.md).

## Install

```bash
git clone https://github.com/dphdame/forking-paths.git
cd forking-paths
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Use

```bash
# Find your session logs
forking-paths list-sessions

# Audit one session
forking-paths audit ~/.claude/projects/-Users-yourname/<session-id>.jsonl --out provenance.md

# Or write to stdout
forking-paths audit <log>.jsonl
```

Attach `provenance.md` as a supplemental file to a working paper, commit it alongside your replication package, or use it for your own pre-submission review.

## What this tool is not

- **Not a fraud detector.** Session logs are editable. The SHA-256 commits to the log at the moment the report is generated; a determined bad actor edits and re-hashes. The tool serves honest researchers who want to demonstrate discipline and self-auditors who want to check their own work before submitting.
- **Not a replacement for pre-registration.** Pre-registration says what was committed to before seeing data. This tool surfaces what was actually considered while doing the work. They complement each other.
- **Not a p-hacking detector.** It surfaces the decision graph; it does not evaluate whether the decisions were correct.
- **Not silent about its heuristic limits.** Flag patterns produce false positives and false negatives. Every report ends with a limitations section that a referee can read.

## Why this exists

At the May 2026 NBER Applications of AI in Healthcare panel, Scott Cunningham flagged that reasoning models keep a running JSON log of every choice they make on the way to a result, and that those logs are "full of specification searching." Telling a model that prior literature finds a particular result appears to make it quietly abandon specifications pointing the other way. None of that appears in a pre-registration. None of it is visible to a referee. The files are trivially edited or deleted, and no norms or tools currently exist to surface what they contain.

This tool takes the data that already exists by default and turns it into a usable artifact. Standard-setting will come from journal editors (see David Bradford's ASHEcon convening this summer); this is one piece of the tooling layer that has to exist before any standard can be enforced.

## Format support

- **Claude Code session logs** (JSONL, `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`). Working as of May 2026.
- Codex, Cursor, and other agent log formats: not yet supported. PRs welcome.

## Test

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

## License

MIT. Use it, fork it, ship variants.

## Citation

If this tool meaningfully shapes how you report an analysis, a footnote pointing to the repo is appreciated and helps adoption.

```
Cholette, V. (2026). forking-paths: Provenance audit for AI-assisted empirical research. https://github.com/dphdame/forking-paths
```

## Acknowledgments

The JSON-log observation that motivated this tool is Scott Cunningham's, surfaced at the May 8, 2026 NBER panel on AI in healthcare research and discussed in the panel writeup at [franklythecounterfactual.substack.com](https://franklythecounterfactual.substack.com/). The framing in terms of forking paths is Andrew Gelman's. The packaging is the contribution here.
