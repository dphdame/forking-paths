# Pre-Analysis Plan: Instrumental Variables

Starter based on current methodological consensus as of May 2026. Substitute as appropriate for the specific case. Citations at the end.

## Method tag

`iv`

## Research question

> [fill in]

## Procedural commitments

### Instrument set

Lock the instrument set before estimation. State each instrument and what variation it captures.

> [fill in: e.g., "Bartik-style shift-share instrument constructed from 1990 industry shares interacted with national employment growth by industry, 1990 to year-of-observation"]

### Identification narrative

State the three identifying assumptions in plain text. Each gets one paragraph in the paper.

- **Relevance** (instrument predicts treatment): [fill in]
- **Exclusion** (instrument affects outcome only through treatment): [fill in]
- **Monotonicity** (no defiers): [fill in]

### Estimator

Lock the estimator before estimation. Options: `2SLS`, `LIML`, `JIVE`. Default: 2SLS, with LIML reported as sensitivity when the instrument is suspected weak.

> [fill in]

### First-stage diagnostic

Lock the first-stage diagnostic before estimation. Default: effective F-statistic per Montiel Olea & Pflueger (2013), robust to heteroskedasticity and clustering. Conventional Stock-Yogo (2005) critical values apply only under homoskedasticity.

> [fill in: e.g., "Report effective F (Montiel Olea-Pflueger) and compare to 23.1 threshold for 10% worst-case bias of 2SLS"]

### Weak-instrument-robust inference

Lock the weak-instrument-robust inference procedure before estimation. Default: Anderson-Rubin (AR) confidence sets when there is one endogenous regressor. Conditional likelihood ratio (CLR) is also acceptable. tF-adjusted inference per Lee, McCrary, Moreira, & Porter is acceptable for single-instrument 2SLS.

> [fill in: e.g., "Report AR confidence set alongside conventional 2SLS CI; if effective F is below threshold, AR is the headline"]

### Pre-committed robustness ladder

List, in order, the robustness checks committed to before estimation. Conventional ladder for IV:

1. Effective F-statistic per Montiel Olea-Pflueger reported alongside conventional first-stage F
2. AR (or CLR) confidence set reported alongside 2SLS confidence interval
3. LIML estimate reported as sensitivity to weak instruments
4. Reduced-form estimate reported (instrument on outcome directly), to show variation exists
5. Overidentification test (Hansen J) if more than one instrument
6. Alternative instrument set (drop one instrument at a time) if more than one instrument
7. [fill in: any project-specific additional check]

## Substantive commitments specific to this project

### Unit of observation

> [fill in]

### Sample

- Inclusion: [fill in]
- Exclusion: [fill in]
- Time window: [fill in]
- Geography: [fill in]

### Endogenous regressor

- Variable: [fill in]
- Source: [fill in]
- Why endogenous: [fill in: source of bias the instrument is intended to address]

### Primary outcome

- Variable: [fill in]
- Units: [fill in]
- Source: [fill in]

### Controls

> [fill in: covariates included in both stages]

### What would change the conclusion

> [fill in: e.g., "If the effective F falls below the Montiel Olea-Pflueger 10% worst-case-bias threshold, the headline 2SLS coefficient is replaced by the AR confidence set."]

### Stop conditions

> [fill in]

## Citations

- Andrews, I., Stock, J. H., & Sun, L. (2019). Weak instruments in instrumental variables regression: Theory and practice. *Annual Review of Economics*, 11, 727-753.
- Montiel Olea, J. L., & Pflueger, C. (2013). A robust test for weak instruments. *Journal of Business & Economic Statistics*, 31(3), 358-369.
- Stock, J. H., & Yogo, M. (2005). Testing for weak instruments in linear IV regression. In D. W. K. Andrews & J. H. Stock (Eds.), *Identification and Inference for Econometric Models: Essays in Honor of Thomas Rothenberg* (pp. 80-108). Cambridge University Press.
