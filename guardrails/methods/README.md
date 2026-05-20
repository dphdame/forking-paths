# Method-Specific Pre-Registration Starters

Each file in this directory is a starter pre-analysis plan for a specific identification strategy. The starters come pre-populated with procedural commitments that reflect current methodological consensus as of May 2026, and leave the substantive choices (sample, outcome, instrument, running variable) blank for the researcher to fill in.

## How to use

1. Copy the appropriate starter into the project root as `prereg.md`. Or use the CLI:

   ```bash
   forking-paths init --method did --dir .
   ```

2. Fill in every section marked `[fill in]`. Sections left blank will be flagged by `forking-paths audit --prereg`.

3. Lock the prereg before running any specifications. Commit the file to version control alongside the analysis code.

4. After the analysis session, run the audit:

   ```bash
   forking-paths audit <session-log>.jsonl --prereg prereg.md --out provenance.md
   ```

   The provenance report will include a compliance section comparing what was committed to against what actually ran.

## Procedural versus substantive

The starters separate two things:

- **Procedural commitments** are pre-populated. These are choices the methodological literature has converged on for the design class (e.g., for staggered DiD, use Callaway-Sant'Anna or Borusyak-Jaravel-Spiess rather than two-way fixed effects; for RDD, use Calonico-Cattaneo-Titiunik bandwidth selection rather than ad hoc rules). The pre-population is a default, not a mandate. If the project calls for a different choice, override and document why.

- **Substantive commitments** are blank. These are choices the researcher must make for the specific project: which instrument, which running variable, which sample, which outcome. The starter cannot pre-fill these because they are project-specific.

## Contributing

PRs welcome for additional method starters. Plausible additions:

- Synthetic control
- Matching / propensity-score weighting
- Bunching estimators
- Shift-share IV
- Bayesian hierarchical models
- Survival analysis

A useful starter includes:

1. Estimator choice with one-sentence rationale for the default
2. Diagnostic checks specific to the design
3. Robustness ladder in conventional order
4. A "substantive commitments specific to this project" section the researcher fills in
5. Citations to the canonical methodological papers

Style: no em dashes, no contrastive flips, no second-person directives outside of fill-in prompts.
