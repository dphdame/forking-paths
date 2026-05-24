# Session log: 2026-05-23

## Completed

- Gate v2 (DiD) runner + full batch at n=18/arm. Verdict GATE_V2_FAILS.
- Gate v3 Stage 0 (OVB toy) — full pipeline: data generator, system
  prompt, prereg, runner, audit, full batch at n=18/arm.
- Audit-bug patch: HEADLINE `spec=` field added to contrary-reporting
  detection; classifier widened to recognize "adjusted-ols",
  "standardized-ols", "ols-with-x" as `spec2_lincontrol`. Pre- and
  post-patch artifacts both preserved at `analysis/gate_v3_*.PRE-PATCH.*`.
- Cross-family doc consolidation; OVB row + subsection updated across
  CROSS-FAMILY-SUMMARY, STAGE-0-NOTE, STAGE-2-DID-NOTE, STAGE-2-PLAN,
  ARCHITECTURE, PREREG-AMENDMENT.
- Doc pruning pass: stripped Interpretation/Limitations/Implication
  sections from all stage notes, Audience headers, Cunningham frames,
  "honest read" paragraphs in verdict generator and verdict file.
- README rewritten as tools-and-gates index (no results commentary).

## Files modified (committed this session)

- `e19157a` — Gate v3 consolidation: 319 files, +48,046 lines.
- `b23b89b` — Pare public docs: 12 files, -1,104 / +152.

## Decisions made

- Run trials concurrently inside one runner (ThreadPoolExecutor, 8
  workers) rather than spawning Claude Code subagents.
- Strip the staged data README confounder-hint after seeing that bare
  Arm A had 100% contrary_visible in smoke (overly easy task).
- Keep the pre-patch audit CSV and verdict on disk (`.PRE-PATCH.*`)
  rather than overwriting; transparency about the bug fix.
- Defer cross-family results writeup; strip editorial framing from
  public docs.

## Open items (not in scope for this session)

- The experiments/gate-drift-evaluation/ directory is not promised in
  the public LinkedIn post and is not needed to use the tool. Decision
  on whether to remove it from the public repo (option 1) or keep but
  bury (option 2) is pending.
- `src/forking_paths/ledger_audit.py` was added during this session
  but belongs in the experiment directory (it is not part of the
  `forking-paths audit` CLI the post describes). Pending move.
- Stage 2 DiD and Event Study locked primaries remain credit-limited
  at n=2/3 and n=1/4 clean sessions respectively. Resolvable by
  re-running with restored API credit; no code changes needed.

## Extracted artifacts

None this session. Work was repo-specific.
