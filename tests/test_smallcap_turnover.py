from datetime import date

import pandas as pd
import pytest


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "market": ["a_share"] * 3 + ["us"],
            "symbol": ["A", "B", "C", "US"],
            "date": [date(2026, 1, 2)] * 4,
            "close": [1.0] * 4,
            "volume": [100.0] * 4,
            "turnover": [10.0, 20.0, 30.0, 1_000.0],
            "market_cap": [100.0, 200.0, 300.0, 1.0],
            "currency": ["CNY", "CNY", "CNY", "USD"],
            "is_tradable": [True] * 4,
            "is_suspended": [False] * 4,
            "source": ["fixture"] * 4,
        }
    )


def test_smallcap_turnover_stats_ranks_a_share_by_market_cap():
    from market_research.smallcap_turnover import build_smallcap_turnover_stats

    result = build_smallcap_turnover_stats(_panel(), rank_counts=(2, 4))

    assert result[["rank_count", "selected_count"]].to_dict("records") == [
        {"rank_count": 2, "selected_count": 2},
        {"rank_count": 4, "selected_count": 3},
    ]
    row = result.iloc[0]
    assert row["date"] == "2026-01-02"
    assert row["eligible_count"] == 3
    assert row["turnover_sum"] == pytest.approx(30.0)
    assert row["turnover_mean"] == pytest.approx(15.0)
    assert row["turnover_median"] == pytest.approx(15.0)
    assert row["market_cap_median"] == pytest.approx(150.0)


def test_smallcap_turnover_stats_rejects_invalid_rank_counts():
    from market_research.smallcap_turnover import build_smallcap_turnover_stats

    with pytest.raises(ValueError, match="rank_counts"):
        build_smallcap_turnover_stats(_panel(), rank_counts=(0, 2))


def test_smallcap_turnover_default_includes_single_smallest_stock():
    from market_research.smallcap_turnover import build_smallcap_turnover_stats

    result = build_smallcap_turnover_stats(_panel())

    assert result["rank_count"].tolist() == [1, 10, 50, 100, 200, 400, 1000]
    row = result.loc[result["rank_count"].eq(1)].iloc[0]
    assert row["selected_count"] == 1
    assert row["turnover_median"] == pytest.approx(10.0)
