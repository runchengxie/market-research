from datetime import date

import pandas as pd


def test_quality_preserves_missing_observation_as_issue_not_zero():
    from market_research.quality import profile_panel

    frame = pd.DataFrame(
        {
            "market": ["us", "us"],
            "symbol": ["ABC", "ABC"],
            "date": [date(2026, 1, 1), date(2026, 1, 2)],
            "close": [1.0, 1.0],
            "volume": [10.0, None],
            "turnover": [10.0, None],
            "market_cap": [100.0, 100.0],
            "currency": ["USD", "USD"],
            "is_tradable": [True, False],
            "is_suspended": [False, True],
            "source": ["fixture", "fixture"],
        }
    )

    profile = profile_panel(frame)

    assert profile["rows"] == 2
    assert profile["missing_turnover_rows"] == 1
    assert profile["zero_turnover_rows"] == 0
