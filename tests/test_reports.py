from datetime import date
from pathlib import Path

import pandas as pd


def test_build_liquidity_report_is_stable_and_separates_markets():
    from market_research.contracts import PanelMetadata
    from market_research.reports import build_liquidity_report

    panel = pd.DataFrame(
        {
            "market": ["us", "us"],
            "symbol": ["A", "B"],
            "date": [date(2026, 1, 1)] * 2,
            "close": [1.0, 2.0],
            "volume": [100.0, 200.0],
            "turnover": [100.0, 400.0],
            "market_cap": [1_000_000.0, 20_000_000.0],
            "currency": ["USD"] * 2,
            "is_tradable": [True, True],
            "is_suspended": [False, False],
            "source": ["fixture"] * 2,
            "medadv20": [50.0, 200.0],
        }
    )
    metadata = PanelMetadata(
        source="fixture", as_of="2026-01-01", currency="USD", universe_filter="all",
        fx_method="native", feature_lag=1, coverage_start="2026-01-01",
        coverage_end="2026-01-01", calendar_mode="explicit", quality_status="verified",
    )

    report = build_liquidity_report({"us": panel}, {"us": metadata})

    assert report["markets"] == ["us"]
    assert report["summary"][0]["market"] == "us"
    assert report["summary"][0]["turnover_median"] == 250.0
    assert report["metadata"]["us"]["currency"] == "USD"
    assert "capacity_surface" in report


def test_write_report_bundle_writes_json_and_csv(tmp_path: Path):
    from market_research.reports import write_report_bundle

    report = {"markets": ["us"], "summary": [{"market": "us", "rows": 1}], "metadata": {}}

    write_report_bundle(report, tmp_path)

    assert (tmp_path / "liquidity_report.json").exists()
    assert (tmp_path / "liquidity_summary.csv").exists()
    assert (tmp_path / "coverage_diagnostics.csv").exists()
    assert (tmp_path / "capacity_surface.csv").exists()
