from pathlib import Path

import pandas as pd


def test_indices_report_writes_legacy_snapshot_family(tmp_path: Path):
    from market_research.cli import main

    source = tmp_path / "index.parquet"
    pd.DataFrame({"ts_code": ["000300.SH"] * 2, "trade_date": ["20260102", "20260106"], "close": [100, 121]}).to_parquet(source)
    config = tmp_path / "config.toml"
    output = tmp_path / "outputs"
    config.write_text(f'output_root = "{output}"\n[index_research]\nindex_daily_path = "{source}"\n', encoding="utf-8")

    assert main(["report", "indices", "--config", str(config)]) == 0
    assert (output / "a_share_index_price_returns.csv").exists()


def test_cashflow_report_writes_status_and_frequency_outputs(tmp_path: Path):
    from market_research.cli import main

    source = tmp_path / "cashflow.parquet"
    pd.DataFrame({"ts_code": ["932365.CSI"] * 2, "trade_date": ["20250102", "20260105"], "close": [100, 110]}).to_parquet(source)
    config = tmp_path / "config.toml"
    output = tmp_path / "outputs"
    config.write_text(f'output_root = "{output}"\n[index_research]\nlinked_index_daily_path = "{source}"\n', encoding="utf-8")

    assert main(["report", "cashflow", "--config", str(config)]) == 0
    assert (output / "cashflow_indices" / "cashflow_data_status.csv").exists()


def test_cli_help_lists_migrated_fetch_commands(capsys):
    from market_research.cli import main

    assert main(["fetch", "--help"]) == 0
    assert "linked-indices" in capsys.readouterr().out
