from pathlib import Path

import pandas as pd


def test_indices_report_writes_legacy_snapshot_family(tmp_path: Path):
    from market_research.cli import main

    source = tmp_path / "index.parquet"
    pd.DataFrame({"ts_code": ["000300.SH"] * 2, "trade_date": ["20260102", "20260106"], "close": [100, 121]}).to_parquet(source)
    etf_daily = tmp_path / "etf.parquet"
    factors = tmp_path / "factors.parquet"
    basic = tmp_path / "basic.csv"
    pd.DataFrame({"ts_code": ["510001.SH"] * 2, "trade_date": ["20260102", "20260106"], "close": [10, 11]}).to_parquet(etf_daily)
    pd.DataFrame({"ts_code": ["510001.SH"] * 2, "trade_date": ["20260102", "20260106"], "adj_factor": [1, 1.1]}).to_parquet(factors)
    pd.DataFrame({"ts_code": ["510001.SH"], "name": ["示例ETF"], "benchmark": ["沪深300指数"], "status": ["L"], "fund_type": ["股票型"], "list_date": [20200101]}).to_csv(basic, index=False)
    config = tmp_path / "config.toml"
    output = tmp_path / "outputs"
    config.write_text(f'output_root = "{output}"\n[index_research]\nindex_daily_path = "{source}"\netf_daily_path = "{etf_daily}"\netf_adj_factor_path = "{factors}"\netf_basic_path = "{basic}"\nindex_start_date = "20260102"\nindex_end_date = "20260106"\n', encoding="utf-8")

    assert main(["report", "indices", "--config", str(config)]) == 0
    assert (output / "a_share_index_price_returns.csv").exists()
    assert (output / "etf_proxy_returns.csv").exists()


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


def test_etf_pairs_report_writes_all_legacy_pairing_outputs(tmp_path: Path):
    from market_research.cli import main

    catalog = tmp_path / "catalog.csv"
    basic = tmp_path / "basic.csv"
    daily = tmp_path / "etf.parquet"
    factors = tmp_path / "factors.parquet"
    index = tmp_path / "index.parquet"
    pd.DataFrame({"ts_code": ["000300.SH"], "indx_name": ["沪深300指数"]}).to_csv(catalog, index=False)
    pd.DataFrame({"ts_code": ["510001.SH"], "name": ["示例ETF"], "benchmark": ["沪深300指数"], "status": ["L"], "fund_type": ["股票型"], "list_date": [20150101]}).to_csv(basic, index=False)
    pd.DataFrame({"ts_code": ["510001.SH"] * 2, "trade_date": ["20260102", "20260106"], "close": [10, 11], "amount": [20_000, 20_000]}).to_parquet(daily)
    pd.DataFrame({"ts_code": ["510001.SH"] * 2, "trade_date": ["20260102", "20260106"], "adj_factor": [1, 1.1]}).to_parquet(factors)
    pd.DataFrame({"ts_code": ["000300.SH"] * 2, "trade_date": ["20260102", "20260106"], "close": [100, 105]}).to_parquet(index)
    config = tmp_path / "config.toml"
    output = tmp_path / "outputs"
    config.write_text(f'output_root = "{output}"\n[index_research]\nindex_catalog_path = "{catalog}"\netf_basic_path = "{basic}"\netf_daily_path = "{daily}"\netf_adj_factor_path = "{factors}"\nindex_daily_path = "{index}"\nindex_start_date = "20260102"\nindex_end_date = "20260106"\n', encoding="utf-8")

    assert main(["report", "etf-pairs", "--config", str(config)]) == 0
    assert (output / "linked_indices" / "etf_index_pairing.csv").exists()
    assert (output / "linked_indices" / "paired_index_etf_returns_all.csv").exists()
    assert (output / "linked_indices" / "paired_index_etf_representatives.csv").exists()
