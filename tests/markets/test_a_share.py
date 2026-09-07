from pathlib import Path

import pandas as pd
import pytest


def test_a_share_adapter_converts_units_and_filters(tmp_path: Path):
    from market_research.markets.a_share import build_a_share_panel

    source = tmp_path / "000001.SZ.parquet"
    pd.DataFrame(
        {
            "trade_date": ["2026-01-01", "2026-01-02"],
            "close": [10.0, 11.0],
            "adj_close": [10.0, 11.0],
            "amount": [1000.0, 2000.0],
            "total_mv": [5000.0, 6000.0],
            "is_st": [False, True],
            "is_suspended": [False, False],
        }
    ).to_parquet(source)

    panel, metadata = build_a_share_panel(tmp_path)

    assert len(panel) == 1
    assert panel.loc[0, "turnover"] == 1_000_000
    assert panel.loc[0, "market_cap"] == 50_000_000
    assert panel.loc[0, "close"] == 10.0
    assert panel.loc[0, "adj_close"] == 10.0
    assert metadata.currency == "CNY"


def test_a_share_adapter_accepts_one_parquet_file(tmp_path: Path):
    from market_research.markets.a_share import build_a_share_panel

    source = tmp_path / "000001.SZ.parquet"
    pd.DataFrame(
        {
            "trade_date": ["2026-01-01"], "close": [10.0], "adj_close": [10.0],
            "amount": [1000.0], "total_mv": [5000.0], "is_st": [False], "is_suspended": [False],
        }
    ).to_parquet(source)

    panel, _ = build_a_share_panel(source)

    assert len(panel) == 1


def test_a_share_adapter_can_scan_directory_with_duckdb(tmp_path: Path):
    pytest.importorskip("duckdb")
    from market_research.markets.a_share import build_a_share_panel

    for symbol, close in [("000001.SZ", 10.0), ("000002.SZ", 20.0)]:
        pd.DataFrame(
            {
                "ts_code": [symbol], "trade_date": ["2026-01-01"], "close": [close],
                "adj_close": [close], "vol": [100.0], "amount": [1000.0],
                "total_mv": [5000.0], "is_st": [False], "is_suspended": [False],
            }
        ).to_parquet(tmp_path / f"{symbol}.parquet")

    panel, _ = build_a_share_panel(tmp_path, use_duckdb=True)

    assert set(panel["symbol"]) == {"000001.SZ", "000002.SZ"}
