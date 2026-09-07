from pathlib import Path


def test_us_adapter_calculates_notional_and_market_cap(tmp_path: Path):
    from market_research.markets.us import build_us_panel

    source = tmp_path / "shareprices.csv"
    source.write_text(
        "Ticker;Date;Close;Volume;Shares Outstanding\n"
        "ABC;2026-01-01;2;100;1000\n"
        "PENNY;2026-01-01;0.5;100;1000\n",
        encoding="utf-8",
    )

    panel, metadata = build_us_panel(source)

    assert list(panel["symbol"]) == ["ABC"]
    assert panel.loc[0, "turnover"] == 200
    assert panel.loc[0, "market_cap"] == 2000
    assert metadata.currency == "USD"
