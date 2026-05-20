# Pre-Analysis Plan

## Research question

Does state-level minimum wage increase reduce teen employment in non-metro counties between 2010 and 2024?

## Method

`did`

## Unit of observation

County-year.

## Sample

- Inclusion: Non-MSA counties in the 50 states plus DC, 2010 through 2024.
- Exclusion: Counties with fewer than 5,000 teen residents in any sample year.
- Time window: 2010 to 2024.
- Geography: 50 states plus DC, non-MSA counties only.

## Primary outcome

- Variable: `teen_employment_rate`
- Units: Share of 16-19 year olds employed.
- Source: BLS Local Area Unemployment Statistics.

## Primary specification

Two-way fixed-effect (TWFE) DiD with county and year fixed effects, treatment indicator equal to 1 in years after a state minimum wage change. Standard errors clustered at state level.

## Robustness ladder

1. Callaway-Sant'Anna heterogeneity-robust estimator. Tests for negative-weight contamination in TWFE.
2. Event-study specification with five pre-treatment leads and five post-treatment lags. Tests for parallel pre-trends.
3. Alternative control set restricted to never-treated counties only. Tests sensitivity to not-yet-treated comparisons.
4. Roth (2022) sensitivity bounds on parallel-trends assumption. Characterizes robustness to PT violation.

## What would change the conclusion

If the Callaway-Sant'Anna estimator returns an ATT of opposite sign from the TWFE primary, the headline finding does not hold. If the parallel-trends test rejects at the 5% level using five pre-treatment leads, the identification assumption is undermined.

## Stop conditions

After the primary TWFE specification and the four locked robustness checks, the analysis stops. Any additional specification requires a written methodological justification.
