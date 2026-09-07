from datetime import date

import pandas as pd
import pytest


def _panel():
    return pd.DataFrame(
        {
            "market": ["a_share"] * 6,
            "symbol": ["A", "B", "A", "B", "A", "B"],
            "date": [date(2026, 1, 1), date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 2), date(2026, 1, 3), date(2026, 1, 3)],
            "close": [10.0, 20.0, 11.0, 20.0, 12.0, 22.0],
            "adj_close": [10.0, 20.0, 11.0, 20.0, 12.0, 22.0],
            "volume": [100.0] * 6,
            "turnover": [1000.0] * 6,
            "market_cap": [100.0, 200.0, 100.0, 200.0, 100.0, 200.0],
            "currency": ["CNY"] * 6,
            "is_tradable": [True] * 6,
            "is_suspended": [False] * 6,
            "is_st": [False] * 6,
            "source": ["fixture"] * 6,
        }
    )


def test_reconstruct_smallest_cap_index_uses_next_market_day():
    from market_research.indexes import reconstruct_smallest_cap_index

    result = reconstruct_smallest_cap_index(_panel(), constituent_count=1)

    assert list(result["date"]) == [date(2026, 1, 1), date(2026, 1, 2)]
    assert result.loc[0, "selected_count"] == 1
    assert result.loc[0, "priced_count"] == 1
    assert result.loc[0, "return"] == pytest.approx(0.1)


def test_summarize_nav_reports_underwater_episode():
    from market_research.indexes import build_underwater_periods, summarize_nav

    nav = pd.DataFrame({"date": ["2026-01-01", "2026-01-02", "2026-01-03"], "nav": [1.0, 0.8, 1.1]})

    episodes = build_underwater_periods(nav)
    summary = summarize_nav(nav)

    assert len(episodes) == 1
    assert summary["max_drawdown"] == pytest.approx(-0.2)


def test_reconstruct_smallest_cap_index_from_parquet(tmp_path):
    pytest.importorskip("duckdb")
    from market_research.indexes import reconstruct_smallest_cap_index_from_parquet

    for symbol, values in {
        "000001.SZ": [("2026-01-01", 10.0), ("2026-01-02", 11.0)],
        "000002.SZ": [("2026-01-01", 20.0), ("2026-01-02", 20.0)],
    }.items():
        pd.DataFrame(
            {
                "ts_code": [symbol, symbol],
                "trade_date": [date for date, _ in values],
                "adj_close": [close for _, close in values],
                "total_mv": [100.0 if symbol.startswith("000001") else 200.0] * 2,
                "is_st": [False, False],
                "is_suspended": [False, False],
            }
        ).to_parquet(tmp_path / f"{symbol}.parquet")

    result = reconstruct_smallest_cap_index_from_parquet(tmp_path, constituent_count=1)

    assert result.loc[0, "return"] == pytest.approx(0.1)
