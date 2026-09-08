from pathlib import Path

import pandas as pd


def test_jp_adapter_maps_jquants_daily_fields_and_keeps_missing_market_cap(tmp_path: Path):
    from market_research.markets.jp import build_jp_panel

    daily = tmp_path / "daily" / "2026"
    daily.mkdir(parents=True)
    pd.DataFrame(
        {
            "Date": ["2026-01-01", "2026-01-02"],
            "Code": [13010, 13010],
            "C": [100.0, 101.0],
            "Vo": [1000.0, 1100.0],
            "Va": [100000.0, None],
        }
    ).to_parquet(daily / "equities_bars_daily_202601.parquet")

    panel, metadata = build_jp_panel(tmp_path)

    assert list(panel["symbol"]) == ["13010", "13010"]
    assert panel.loc[0, "close"] == 100.0
    assert panel.loc[0, "volume"] == 1000.0
    assert panel.loc[0, "turnover"] == 100000.0
    assert pd.isna(panel.loc[1, "turnover"])
    assert panel["currency"].unique().tolist() == ["JPY"]
    assert metadata.quality_status == "incomplete"


def test_jp_adapter_respects_as_of(tmp_path: Path):
    from market_research.markets.jp import build_jp_panel

    daily = tmp_path / "daily" / "2026"
    daily.mkdir(parents=True)
    pd.DataFrame(
        {"Date": ["2026-01-01", "2026-01-02"], "Code": [13010, 13010], "C": [100.0, 101.0], "Vo": [1000.0, 1100.0], "Va": [100000.0, 110000.0]}
    ).to_parquet(daily / "equities_bars_daily_202601.parquet")

    panel, _ = build_jp_panel(tmp_path, as_of="2026-01-01")

    assert len(panel) == 1


def test_jp_adapter_joins_optional_market_cap_sidecar(tmp_path: Path):
    from market_research.markets.jp import build_jp_panel

    daily = tmp_path / "daily" / "2026"
    daily.mkdir(parents=True)
    pd.DataFrame(
        {"Date": ["2026-01-02"], "Code": [13010], "C": [100.0], "Vo": [1000.0], "Va": [100000.0]}
    ).to_parquet(daily / "equities_bars_daily_2026.parquet")
    valuation = tmp_path / "market_cap.parquet"
    pd.DataFrame(
        {"Date": ["2026-01-02"], "Code": ["13010"], "MarketCap": [2_000_000_000.0]}
    ).to_parquet(valuation)

    panel, metadata = build_jp_panel(tmp_path, market_cap_path=valuation)

    assert panel.loc[0, "market_cap"] == 2_000_000_000.0
    assert metadata.quality_status == "verified"
