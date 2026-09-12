# Barra-like A-share Risk Model Design

## Status

Design approved in conversation on 2026-09-12. This document defines the
boundary for a staged implementation; it is not a claim of compatibility with
any commercial Barra product.

## Objective

Build a reproducible, PIT-aware A-share risk-analysis capability that explains
the risk of the official cash-flow sleeve, active cash-flow strategy,
self-built microcap100, 60/40 cash-flow/microcap mixes, and eventually
DailyWatch20.

The first release is a Barra-like research model. It must report data quality,
coverage and limitations alongside exposures and risk numbers.

## Ownership boundary

### quant-platform: generic risk-model kernel

The platform owns market-independent contracts and calculations:

- dated asset/factor exposure matrices;
- cross-sectional WLS factor-return estimation;
- equality and industry-neutral regression options;
- factor covariance estimation with declared window and shrinkage;
- specific-risk estimation from residual returns;
- portfolio exposure, factor risk contribution and marginal-risk calculations;
- versioned result objects and validation errors.

The platform must not contain A-share-specific factor definitions, private
strategy names, supplier paths, or proprietary research parameters.

### quant-market-research: A-share factor adapter and public report

This repository owns:

- A-share factor construction from canonical external panels;
- market-cap, value, momentum, quality, cash-flow, growth, volatility,
  liquidity, leverage and dividend definitions;
- historical industry and security-status handling;
- PIT/freshness/coverage diagnostics;
- `market-research report barra-risk` orchestration;
- public-safe derived reports and provenance manifests.

The report layer consumes the platform kernel through stable APIs and writes
derived output outside the repository unless a deliberately reviewed public
snapshot is requested.

### quant-research: private strategy adapter

This repository owns private strategy holdings and strategy-specific metadata:

- active cash-flow portfolio holdings;
- pure microcap100 and composite microcap holdings;
- DailyWatch20 holdings and private model lineage;
- private portfolio-risk reports and allocation experiments.

It may depend on the released platform kernel and the market-research factor
contract, but must not make `quant-market-research` import private strategy
modules or private holdings.

## Version 1 scope

The minimum usable release includes:

1. market beta;
2. size;
3. industry one-hot exposures;
4. liquidity;
5. low volatility;
6. a quality/cash-flow proxy when PIT coverage passes validation;
7. daily factor returns;
8. rolling factor covariance;
9. specific volatility;
10. portfolio exposure and factor-risk attribution.

Value, momentum, growth, leverage and dividend factors are included in the
contract from the start but may be marked `not_available` until their PIT
inputs pass the same checks.

## Data contract

The canonical exposure panel must have one row per `(as_of_date, symbol,
factor_name)` in long form, or an equivalent wide form with an explicit schema
adapter. Required metadata:

- `as_of_date`: date on which the exposure is available for a decision;
- `symbol`: normalized tradable identifier;
- `factor_name` and numeric `exposure`;
- `industry_code` and `industry_version` when industry factors are used;
- `market_cap` or the source field used for size;
- `eligible`, `is_st`, `is_suspended`, and `is_tradable` flags;
- `source_id`, `source_version`, and `pit_status`.

The return panel must contain:

- `trade_date`, `symbol`, `total_return`;
- a declared price and corporate-action basis;
- missing-return and delisting treatment;
- source and coverage metadata.

The portfolio input must contain:

- `portfolio_id`, `as_of_date`, `symbol`, `weight`;
- gross exposure and cash weight;
- turnover/cost metadata when available;
- strategy provenance without importing private strategy code.

## Calculation design

### Exposure construction

Each raw style factor is winsorized, standardized cross-sectionally and, where
declared, neutralized against industry and market-cap effects. The output must
retain both raw and transformed-factor metadata. No future prices or revised
financial observations may enter a formation-date exposure.

### Factor returns

For each date, estimate:

`asset_return = industry_returns + style_exposures × style_factor_returns + residual`

using WLS with an explicit eligibility mask. The regression receipt must store
the observation count, weighted R-squared, condition number, dropped columns,
and residual diagnostics. Ill-conditioned or under-covered dates are marked
unusable rather than silently imputed.

### Risk model

Estimate factor covariance from factor-return history using a declared rolling
window and EWMA half-life. Apply a documented shrinkage rule before inversion.
Estimate specific risk from residual returns with a minimum-observation rule.
Return both the covariance matrix and its diagnostics.

### Portfolio attribution

For every portfolio/date, output:

- factor exposure vector;
- factor variance and total variance;
- factor risk contribution and percentage contribution;
- specific-risk contribution;
- marginal risk by factor;
- active exposure versus the selected benchmark;
- factor P&L attribution over requested holding windows.

## Research outputs

The first report bundle should include:

- `risk_model_summary.json`;
- `factor_exposures.csv`;
- `factor_returns.csv`;
- `factor_covariance.parquet`;
- `specific_risk.csv`;
- `portfolio_risk_attribution.csv`;
- `coverage_diagnostics.csv`;
- `source_manifest.json`.

The report must explicitly distinguish:

- official 980092 index exposure;
- active self-built cash-flow exposure;
- pure microcap100 exposure;
- composite microcap exposure;
- DailyWatch20 exposure.

## Staged implementation

### Stage 1: platform kernel contract

Implement typed contracts and pure calculations with synthetic fixtures:

- exposure validation;
- WLS factor returns;
- covariance and specific risk;
- portfolio attribution.

No A-share source paths or private strategy names are allowed in this stage.

### Stage 2: A-share adapter

Implement the A-share panel adapter and `barra-risk` report in
`quant-market-research`. Start with market, size, industry, liquidity and
low-volatility factors. Produce coverage and PIT-quality flags before adding
financial factors.

### Stage 3: private strategy integration

Add a thin adapter in `quant-research` that exports versioned portfolio inputs
and consumes the risk report. Analyze cash-flow/microcap mixes first; keep
DailyWatch20 shadow-only until its historical inputs meet the same coverage
standard.

### Stage 4: extension and validation

Add value, momentum, quality, growth, leverage and dividend exposures; run
rolling out-of-sample attribution; add capacity and execution overlays; compare
factor explanations across regimes.

## Testing and acceptance criteria

- synthetic regression recovers known factor returns within tolerance;
- covariance output is symmetric and positive semi-definite after shrinkage;
- specific risk is non-negative and coverage-limited;
- portfolio factor contributions reconcile to modeled risk within tolerance;
- missing/PIT-invalid dates are surfaced in diagnostics;
- no private strategy data enters `quant-market-research`;
- official index replication and active strategy returns remain separate;
- all outputs include source, version, date coverage and research-status
  metadata.

## Known limitations

This model will not be commercial Barra-compatible without the same vendor
definitions, data, and estimation choices. Historical financial PIT coverage is
expected to be the largest limitation. Industry neutrality also does not imply
that a portfolio is industry-neutral unless the portfolio optimization or
attribution explicitly imposes that constraint.
