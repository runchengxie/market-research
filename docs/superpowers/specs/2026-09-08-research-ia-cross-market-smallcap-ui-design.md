# Research IA and Cross-Market Small-Cap Liquidity UI Design

## Decision

The public research portal has three domains: cashflow strategy exploration,
small-cap strategy exploration, and cross-market exploration. Small-cap has two
subtabs: A-share small-cap and cross-market small-cap liquidity.

The cross-market small-cap page compares date-wise market-cap buckets using
lagged ADV20, USD display, explicit FX/provenance, and common-period status. It
uses HK cold data and Japanese NIRA as real input sources when available, while
preserving market-specific data caveats.

## UI behavior

The overview emphasizes the three domains with editorial cards and status
badges. The small-cap page exposes its two subtabs. The cross-market subtab
offers `最新`, `2020–2024`, `2025`, and `2026 YTD`; unavailable periods are
disabled or visibly marked `incomplete` rather than hidden.

The primary UI language is Chinese. English remains only for technical names,
tickers, currencies, and source identifiers.

## Non-goals

This change does not create a production strategy, execute orders, infer
capacity from ADV, or equate ETF proxy allocation with country-level equity
market performance.
