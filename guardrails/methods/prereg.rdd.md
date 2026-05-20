# Pre-Analysis Plan: Regression Discontinuity Design

Starter based on current methodological consensus as of May 2026. Substitute as appropriate for the specific case. Citations at the end.

## Method tag

`rdd`

## Research question

> [fill in]

## Procedural commitments

### Sharp vs fuzzy

Tag one of: `sharp`, `fuzzy`. State why.

> [fill in]

### Bandwidth selection

Lock the bandwidth selector before estimation. Default: Calonico, Cattaneo, & Titiunik (2014) MSE-optimal bandwidth via `rdrobust`. Document the alternative if a different selector is used (CER-optimal, Imbens & Kalyanaraman 2012).

> [fill in: chosen selector]

### Polynomial order

Default: local linear (polynomial order 1). Order 2 requires explicit justification (e.g., visual evidence of curvature near the cutoff that local linear cannot capture).

> [fill in]

### Kernel

Default: triangular kernel. Document if uniform or Epanechnikov is used instead.

> [fill in]

### Donut specification

State whether observations within a window around the cutoff are excluded (donut RD), and if so, the donut radius.

> [fill in, e.g., "no donut" or "exclude observations within 0.5 units of the cutoff to test heaping sensitivity"]

### Manipulation tests

Lock the manipulation diagnostic before estimation. Default: Cattaneo, Jansson & Ma (2020) local-polynomial density test via `rddensity`. Optional companion: McCrary (2008) density test for comparability with older literature.

> [fill in]

### Placebo cutoffs

Lock the set of placebo cutoffs to be tested. Typical practice: test at three placebo points on each side of the true cutoff, away from any other policy thresholds.

> [fill in]

### Pre-committed robustness ladder

List, in order, the robustness checks committed to before estimation. Conventional ladder for RDD:

1. Robust bias-corrected inference (Calonico, Cattaneo & Titiunik 2014) — primary inference uses bias-corrected CIs, not conventional CIs
2. CER-optimal bandwidth as sensitivity — tests sensitivity to bandwidth-selection criterion
3. Alternative polynomial order (1 if primary is 2; 2 if primary is 1) — tests functional-form sensitivity
4. Donut specification at one alternative radius — tests sensitivity to heaping or behavioral response near the cutoff
5. Placebo cutoffs at pre-locked points — tests for spurious discontinuities
6. Covariate-balance test at the cutoff — confirms no observable jumps in pre-determined covariates
7. [fill in: any project-specific additional check]

## Substantive commitments specific to this project

### Unit of observation

> [fill in]

### Sample

- Inclusion: [fill in]
- Exclusion: [fill in]
- Time window: [fill in]
- Geography: [fill in]

### Running variable

- Variable: [fill in]
- Source: [fill in]
- Cutoff: [fill in]
- Justification for cutoff: [fill in: institutional source of the discontinuity]

### Primary outcome

- Variable: [fill in]
- Units: [fill in]
- Source: [fill in]

### Treatment status at the cutoff

> [fill in: who is assigned treatment on each side; what is the compliance rate if fuzzy]

### What would change the conclusion

> [fill in: e.g., "If the manipulation test rejects continuity of the density at the cutoff at the 5% level, the identification assumption is undermined and the headline estimate is not interpretable as causal."]

### Stop conditions

> [fill in]

## Citations

- Calonico, S., Cattaneo, M. D., & Titiunik, R. (2014). Robust nonparametric confidence intervals for regression-discontinuity designs. *Econometrica*, 82(6), 2295-2326.
- Cattaneo, M. D., Idrobo, N., & Titiunik, R. (2020). *A Practical Introduction to Regression Discontinuity Designs: Foundations*. Cambridge University Press.
- Cattaneo, M. D., Jansson, M., & Ma, X. (2020). Simple local polynomial density estimators. *Journal of the American Statistical Association*, 115(531), 1449-1455.
- Imbens, G., & Kalyanaraman, K. (2012). Optimal bandwidth choice for the regression discontinuity estimator. *Review of Economic Studies*, 79(3), 933-959.
- McCrary, J. (2008). Manipulation of the running variable in the regression discontinuity design: A density test. *Journal of Econometrics*, 142(2), 698-714.
