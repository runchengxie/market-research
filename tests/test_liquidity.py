from datetime import date, timedelta

import pandas as pd


def _panel():
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(4)]
    return pd.DataFrame(
        {
            "market": ["us"] * 4,
            "symbol": ["ABC"] * 4,
            "date": dates,
            "close": [1.0] * 4,
            "volume": [10.0, 20.0, 30.0, 40.0],
            "turnover": [100.0, 200.0, 300.0, 400.0],
            "market_cap": [1000.0] * 4,
            "currency": ["USD"] * 4,
            "is_tradable": [True] * 4,
            "is_suspended": [False] * 4,
            "source": ["fixture"] * 4,
        }
    )


def test_lagged_liquidity_does_not_use_same_day_turnover():
    from market_research.liquidity import add_lagged_liquidity

    result = add_lagged_liquidity(_panel(), windows=(2,))

    assert pd.isna(result.loc[0, "adv2"])
    assert pd.isna(result.loc[1, "adv2"])
    assert result.loc[2, "adv2"] == 150.0
    assert result.loc[3, "adv2"] == 250.0

