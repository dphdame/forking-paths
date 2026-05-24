# Pre-Analysis Plan

Fill in every section before the analysis session begins. Sections left blank or with placeholder text will be flagged by `forking-paths audit --prereg`.

## What the agent will produce alongside this prereg

When the system prompt at `guardrails/system-prompt.md` is loaded, the agent is bound to produce three structured artifacts in its session that the audit (`forking-paths audit --prereg`) cross-checks against this plan:

1. A `SPECS-CANDIDATE:` line before any regression runs, declaring every specification the agent is weighing for this analysis. The robustness ladder below seeds this list; the agent may extend it but every executed spec must be declared or justified inline.
2. A `SPEC-LEDGER:` block at the end of the session listing every spec from SPECS-CANDIDATE with `ran=yes|no`, `headline=<coefficient or n/a>`, `status=KEPT|DROPPED`, and `reason=<one sentence>`. Any declared spec missing from the ledger is flagged as an unlogged drop.
3. A standardized `HEADLINE: estimate=..., sign=..., spec=...` line reflecting the locked primary specification, regardless of whether its sign matches the stated prior.

The audit also enforces the contrary-spec requirement from rule 7 of the system prompt: if any candidate spec would produce a result contradicting the stated directional prior, at least one such spec must be run and reported. The locked primary plus the robustness ladder below should be chosen so that a contrary spec exists by construction.

## Research question

State the research question as one sentence. The sentence should be falsifiable: a finding that would change the answer should be nameable in advance.

> [fill in: e.g., "Does expanding SNAP eligibility to ABAWDs reduce food insecurity among single adults under 50 in non-MSA counties?"]

## Method

Tag the primary identification strategy. One of: `did`, `rdd`, `iv`, `cross-section`, `time-series`, `descriptive`, `other`. If the tag is `did`, `rdd`, or `iv`, also fill in the method-specific starter from `guardrails/methods/`.

> [fill in: e.g., `did`]

## Unit of observation

State the unit at which outcomes are measured (individual, household, county-year, firm-month, etc.).

> [fill in]

## Sample

State inclusion and exclusion criteria, time window, and geography. This is the locked sample. Any restriction added later is a deviation.

- Inclusion: [fill in]
- Exclusion: [fill in]
- Time window: [fill in]
- Geography: [fill in]

## Primary outcome

Name one outcome. Give the variable name as it appears in the dataset, the units, and the source.

- Variable: [fill in, e.g., `food_insecure_12mo`]
- Units: [fill in, e.g., binary 0/1]
- Source: [fill in, e.g., CPS Food Security Supplement]

## Primary specification

Lock the primary specification before estimation. Specify model form, controls, fixed effects, and standard errors.

- Model form: [fill in, e.g., two-way fixed-effect linear probability model]
- Controls: [fill in, e.g., age, sex, race/ethnicity, household size]
- Fixed effects: [fill in, e.g., county, year]
- Standard errors: [fill in, e.g., clustered at state level]

## Robustness ladder

List, in order, the robustness checks committed to before estimation. Each entry should include a one-sentence rationale.

1. [fill in: check] — [rationale]
2. [fill in: check] — [rationale]
3. [fill in: check] — [rationale]

## What would change the conclusion

Name the specific finding that would change the answer to the research question. If the primary coefficient flipped sign, what would that imply? If a placebo test rejected, what would that imply?

> [fill in]

## Stop conditions

State when the analysis stops. After the primary plus the locked robustness ladder, no additional specifications are added without writing a justification into the session.

> [fill in: e.g., "After the primary specification and the four locked robustness checks, the analysis stops. Any additional specification requires a written methodological justification."]
