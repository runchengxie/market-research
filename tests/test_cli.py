from pathlib import Path

import json
import pandas as pd


def test_cli_help_returns_success():
    from market_research.cli import main

    assert main(["--help"]) == 0


def test_config_inspect_prints_resolved_output_root(tmp_path: Path, capsys):
    from market_research.cli import main

    assert main(["config", "inspect", "--output-root", str(tmp_path)]) == 0
    assert str(tmp_path) in capsys.readouterr().out


def test_barra_report_writes_summary_and_size_quantiles(tmp_path: Path):
    from market_research.cli import main

    source = tmp_path / "a_share"
    source.mkdir()
    for code, prices, cap in [("000001.SZ", [10, 11], 1), ("000002.SZ", [20, 21], 2)]:
        pd.DataFrame(
            {
                "ts_code": [code, code],
                "trade_date": ["2024-01-01", "2024-01-02"],
                "close": prices,
                "adj_close": prices,
                "vol": [100, 100],
                "amount": [100, 100],
                "total_mv": [cap, cap],
                "is_st": [False] * 2,
                "is_suspended": [False] * 2,
            }
        ).to_parquet(source / f"{code}.parquet", index=False)
    result_root = tmp_path / "barra-results"
    result_root.mkdir()
    (result_root / "manifest.json").write_text(json.dumps({"schema_version": "v1"}), encoding="utf-8")
    (result_root / "meta.json").write_text(json.dumps({"factor_count": 1, "factors": ["size"]}), encoding="utf-8")
    (result_root / "factor_summary.json").write_text(
        json.dumps([{"factor": "size", "geometric_annual_ret": -1.0}]), encoding="utf-8"
    )
    config = tmp_path / "config.toml"
    config.write_text(
        f'output_root = "{tmp_path / "output"}"\nuse_duckdb = false\n\n[sources]\na_share_root = "{source}"\n\n[barra]\nresult_root = "{result_root}"\nsize_quantiles = 2\nholding_period = 1\n',
        encoding="utf-8",
    )

    assert main(["report", "barra", "--config", str(config)]) == 0
    assert (tmp_path / "output" / "barra_summary.json").exists()
    assert (tmp_path / "output" / "barra_size_quantiles.csv").exists()


def test_smallcap_turnover_report_writes_daily_stats_and_summary(tmp_path: Path):
    from market_research.cli import main

    source = tmp_path / "a_share"
    source.mkdir()
    for code, cap in [("000001.SZ", 1), ("000002.SZ", 2), ("000003.SZ", 3)]:
        pd.DataFrame(
            {
                "ts_code": [code, code],
                "trade_date": ["2024-01-01", "2024-01-02"],
                "close": [10, 11],
                "adj_close": [10, 11],
                "vol": [100, 100],
                "amount": [cap * 10, cap * 20],
                "total_mv": [cap, cap],
                "is_st": [False, False],
                "is_suspended": [False, False],
            }
        ).to_parquet(source / f"{code}.parquet", index=False)
    config = tmp_path / "config.toml"
    config.write_text(
        f'output_root = "{tmp_path / "output"}"\nuse_duckdb = false\n\n[sources]\na_share_root = "{source}"\n',
        encoding="utf-8",
    )

    assert main(["report", "smallcap-turnover", "--config", str(config)]) == 0
    daily = pd.read_csv(tmp_path / "output" / "smallcap_turnover_daily.csv")
    assert daily[["date", "rank_count"]].to_dict("records") == [
        {"date": "2024-01-01", "rank_count": 10},
        {"date": "2024-01-01", "rank_count": 50},
        {"date": "2024-01-01", "rank_count": 100},
        {"date": "2024-01-01", "rank_count": 200},
        {"date": "2024-01-01", "rank_count": 400},
        {"date": "2024-01-01", "rank_count": 1000},
        {"date": "2024-01-02", "rank_count": 10},
        {"date": "2024-01-02", "rank_count": 50},
        {"date": "2024-01-02", "rank_count": 100},
        {"date": "2024-01-02", "rank_count": 200},
        {"date": "2024-01-02", "rank_count": 400},
        {"date": "2024-01-02", "rank_count": 1000},
    ]
    assert (tmp_path / "output" / "smallcap_turnover_summary.json").exists()
    manifest = json.loads((tmp_path / "output" / "smallcap_turnover_manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "smallcap_turnover.v1"
    assert manifest["artifacts"][0]["path"] == "smallcap_turnover_daily.csv"
    assert manifest["artifacts"][0]["bytes"] > 0


def test_smallcap_turnover_history_report_marks_partial_eligibility(tmp_path: Path):
    from market_research.cli import main

    daily = tmp_path / "daily"
    basic = tmp_path / "daily_basic"
    daily.mkdir()
    basic.mkdir()
    pd.DataFrame(
        {
            "ts_code": ["000001.SZ", "000002.SZ"],
            "trade_date": [20080102, 20080102],
            "amount": [10.0, 20.0],
        }
    ).to_parquet(daily / "part.parquet", index=False)
    pd.DataFrame(
        {
            "ts_code": ["000001.SZ", "000002.SZ"],
            "trade_date": [20080102, 20080102],
            "total_mv": [100.0, 200.0],
        }
    ).to_parquet(basic / "part.parquet", index=False)
    config = tmp_path / "config.toml"
    config.write_text(
        f'output_root = "{tmp_path / "output"}"\n\n[smallcap_turnover_history]\n'
        f'daily_root = "{daily}"\ndaily_basic_root = "{basic}"\n',
        encoding="utf-8",
    )

    assert main(["report", "smallcap-turnover-history", "--config", str(config)]) == 0
    summary = json.loads((tmp_path / "output" / "smallcap_turnover_history_summary.json").read_text(encoding="utf-8"))
    assert summary["quality_status"] == "incomplete"
    assert "ST" in summary["source"]["universe_filter"]
    assert (tmp_path / "output" / "smallcap_turnover_history_daily.csv").exists()


def test_smallcap_turnover_audit_writes_overlap_summary(tmp_path: Path):
    from market_research.cli import main

    clean = tmp_path / "clean.csv"
    historical = tmp_path / "historical.csv"
    rows = {
        "date": ["2015-01-05", "2015-01-06"],
        "rank_count": [10, 10],
        "selected_count": [10, 10],
        "turnover_median": [100.0, 200.0],
    }
    pd.DataFrame(rows).to_csv(clean, index=False)
    pd.DataFrame({**rows, "turnover_median": [105.0, 160.0]}).to_csv(historical, index=False)
    config = tmp_path / "config.toml"
    config.write_text(
        f'output_root = "{tmp_path / "output"}"\n\n[smallcap_turnover_audit]\n'
        f'clean_daily_path = "{clean}"\nhistorical_daily_path = "{historical}"\n',
        encoding="utf-8",
    )

    assert main(["report", "smallcap-turnover-audit", "--config", str(config)]) == 0
    result = pd.read_csv(tmp_path / "output" / "smallcap_turnover_overlap_audit.csv")
    assert result.loc[0, "common_days"] == 2
    assert result.loc[0, "within_10pct_ratio"] == 0.5
    assert (tmp_path / "output" / "smallcap_turnover_overlap_audit_manifest.json").exists()
