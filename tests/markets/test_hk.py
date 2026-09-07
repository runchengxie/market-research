from pathlib import Path

import pandas as pd


def test_hk_adapter_joins_active_non_etf_and_converts_currency(tmp_path: Path):
    from market_research.markets.hk import build_hk_panel

    daily = tmp_path / "daily"
    valuation = tmp_path / "valuation"
    instruments = tmp_path / "instruments.parquet"
    daily.mkdir()
    valuation.mkdir()
    pd.DataFrame(
        {"trade_date": ["2026-01-01"], "total_turnover": [7800.0]}
    ).to_parquet(daily / "00001.HK.parquet")
    pd.DataFrame(
        {"trade_date": ["2026-01-01"], "hk_total_market_val": [78000.0]}
    ).to_parquet(valuation / "00001.HK.parquet")
    pd.DataFrame(
        {"symbol": ["00001.HK", "ETF.HK"], "status": ["Active", "Active"], "type": ["CS", "ETF"]}
    ).to_parquet(instruments)

    panel, metadata = build_hk_panel(daily, valuation, instruments)

    assert list(panel["symbol"]) == ["00001.HK"]
    assert panel.loc[0, "turnover"] == 7800
    assert panel.loc[0, "market_cap"] == 78000
    assert "7.8" in metadata.fx_method
    assert metadata.currency == "HKD"
