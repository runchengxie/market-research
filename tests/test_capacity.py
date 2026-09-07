from datetime import date

import pandas as pd


def test_capacity_uses_lagged_liquidity_and_marks_missing_rows():
    from market_research.capacity import build_instrument_capacity

    panel = pd.DataFrame(
        {
            "market": ["us", "us", "us"],
            "symbol": ["A", "B", "C"],
            "date": [date(2026, 1, 3)] * 3,
            "turnover": [1000.0, None, 0.0],
            "market_cap": [10000.0, 10000.0, 10000.0],
            "is_tradable": [True, True, False],
            "medadv20": [800.0, None, 0.0],
        }
    )

    result = build_instrument_capacity(panel, (0.1,), (5,))

    assert result.loc[result["symbol"] == "A", "horizon_capacity"].iloc[0] == 400.0
    assert result.loc[result["symbol"] == "B", "capacity_quality"].iloc[0] == "missing_liquidity"
    assert result.loc[result["symbol"] == "C", "capacity_quality"].iloc[0] == "non_tradable"
