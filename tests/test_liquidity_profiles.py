from datetime import date

import pandas as pd
import pytest


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "market": ["a_share", "a_share", "a_share"],
            "symbol": ["A", "B", "C"],
            "date": [date(2026, 1, 2)] * 3,
            "market_cap": [50_000_000, 500_000_000, 20_000_000_000],
            "currency": ["CNY"] * 3,
            "turnover": [1_000_000, 5_000_000, 20_000_000],
            "medadv20": [2_000_000, 6_000_000, 25_000_000],
            "is_tradable": [True] * 3,
        }
    )


def test_bucket_summary_converts_native_values_and_keeps_bucket_order():
    from market_research.liquidity_profiles import build_bucket_summary

    result = build_bucket_summary(_panel(), currency="USD", fx_rate=1 / 7.2)

    assert list(result.loc[result["count"].gt(0), "bucket"]) == ["<1千万", "1千万-1亿", "10亿-100亿"]
    assert result.loc[0, "median_usd"] == pytest.approx(2_000_000 / 7.2)
    assert result.loc[0, "count"] == 1


def test_instrument_diagnostics_ranks_low_liquidity_sub_100m_market_caps():
    from market_research.liquidity_profiles import build_instrument_diagnostics

    result = build_instrument_diagnostics(_panel(), fx_rate=1 / 7.2)

    assert list(result["symbol"]) == ["A", "B"]
    assert result.loc[0, "avg_turnover_usd"] == pytest.approx(2_000_000 / 7.2)
