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
