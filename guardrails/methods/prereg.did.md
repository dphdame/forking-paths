# Pre-Analysis Plan: Difference-in-Differences

Starter based on current methodological consensus as of May 2026. Substitute as appropriate for the specific case. Citations at the end.

## Method tag

`did`

## Research question

> [fill in]

## Procedural commitments

### Estimator choice

Lock the estimator before estimation. Default: with staggered treatment timing, use a heterogeneity-robust estimator from one of:

- Callaway & Sant'Anna (2021) `did` package
- Borusyak, Jaravel & Spiess (2024) imputation estimator
- de Chaisemartin & D'Haultfœuille (2020) `did_multiplegt` estimator

With a single treatment timing and no anticipation, two-way fixed effects (TWFE) is acceptable but should still be checked against a heterogeneity-robust estimator.

> [fill in: chosen estimator and one-sentence reason]

### Treatment timing structure

Tag one of: `single-period`, `staggered`, `continuous`.

> [fill in]

### Control-unit definition

Tag one of: `never-treated`, `not-yet-treated`. Document the reason. Never-treated is the default when a large set of clean controls is available.

> [fill in]

### Event-study window

Lock the number of pre-treatment leads and post-treatment lags reported in the event-study figure.

- Leads: [fill in, e.g., -5 to -1]
- Lags: [fill in, e.g., 0 to +5]

### Pre-period length for parallel-trends evidence

State the minimum number of pre-treatment periods required for the parallel-trends evidence to be credible.

> [fill in, e.g., "at least three pre-treatment periods per cohort"]

### Clustering structure

Lock the clustering level for inference. Default: cluster at the level at which treatment varies.

> [fill in, e.g., "cluster at state level (treatment varies at state-year level)"]

### Aggregation scheme

State which aggregation will be reported as the headline ATT. Options: overall ATT, dynamic ATT (event-time), group-time ATT.

> [fill in]

### Pre-committed robustness ladder

List, in order, the robustness checks committed to before estimation. Conventional ladder for DiD:

1. Heterogeneity-robust estimator (if not primary) — confirms no negative-weight contamination from TWFE
2. Alternative control set (never-treated vs not-yet-treated) — tests sensitivity of comparison group
3. Pre-trends test with Roth (2022) sensitivity bounds — characterizes how much parallel-trends violation would overturn the result
4. Placebo treatment at random pre-period dates — tests for spurious patterns
5. [fill in: any project-specific additional check]

## Substantive commitments specific to this project

### Unit of observation

> [fill in]

### Sample

- Inclusion: [fill in]
- Exclusion: [fill in]
- Time window: [fill in]
- Geography: [fill in]

### Treatment definition

> [fill in: what counts as treated; when treatment turns on]

### Primary outcome

- Variable: [fill in]
- Units: [fill in]
- Source: [fill in]

### Controls

> [fill in]

### What would change the conclusion

> [fill in: e.g., "If the heterogeneity-robust estimator returns an ATT of opposite sign from the TWFE primary, the headline finding does not hold."]

### Stop conditions

> [fill in: after the primary and locked robustness ladder, any additional specification requires written methodological justification]

## Citations

- Borusyak, K., Jaravel, X., & Spiess, J. (2024). Revisiting event-study designs: Robust and efficient estimation. *Review of Economic Studies*, 91(6), 3253-3285.
- Callaway, B., & Sant'Anna, P. H. C. (2021). Difference-in-differences with multiple time periods. *Journal of Econometrics*, 225(2), 200-230.
- de Chaisemartin, C., & D'Haultfœuille, X. (2020). Two-way fixed effects estimators with heterogeneous treatment effects. *American Economic Review*, 110(9), 2964-2996.
- Roth, J. (2022). Pretest with caution: Event-study estimates after testing for parallel trends. *American Economic Review: Insights*, 4(3), 305-322.
