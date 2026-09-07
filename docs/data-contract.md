# Canonical market panel

`market-research` uses one row per `(market, symbol, date)`.

Required columns:

```text
market, symbol, date, close, volume, turnover, market_cap,
currency, is_tradable, is_suspended, source
```

Adapters preserve native currency. Cross-market normalization is a later
calculation and must retain `currency` and `fx_method` in metadata.

The current source mappings are:

| Market | Source fields | Native units |
|---|---|---|
| A-share | `trade_date`, `amount`, `total_mv` | amount: thousand CNY; market cap: ten-thousand CNY |
| HK | `trade_date`, `total_turnover`, `hk_total_market_val` | HKD |
| US | `Date`, `Close`, `Volume`, `Shares Outstanding` | USD |
| JP | `Date`, `Code`, `C`, `Vo`, `Va` | JPY |

`ADV20`, `MedADV20`, `ADV60`, and `MedADV60` are calculated with a one
trading-day lag. Missing observations remain missing. A missing observation is
not evidence of zero trading.

Every report records source, as-of date, coverage, universe filter, currency,
FX method, feature lag, calendar mode, and quality status.
