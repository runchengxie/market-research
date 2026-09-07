from pathlib import Path

import pandas as pd


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
