from pathlib import Path

import pandas as pd


def test_liquidity_report_command_writes_bundle_for_configured_sources(tmp_path: Path):
    from market_research.cli import main

    a_share = tmp_path / "a_share"
    a_share.mkdir()
    pd.DataFrame(
        {"trade_date": ["2026-01-01"], "amount": [1000.0], "total_mv": [5000.0], "is_st": [False], "is_suspended": [False]}
    ).to_parquet(a_share / "000001.SZ.parquet")
    config = tmp_path / "config.toml"
    output = tmp_path / "outputs"
    config.write_text(
        f'output_root = "{output}"\n'
        f'\n[sources]\n'
        f'a_share_root = "{a_share}"\n',
        encoding="utf-8",
    )

    assert main(["report", "liquidity", "--config", str(config)]) == 0
    assert (output / "liquidity_report.json").exists()


def test_validate_command_returns_success_for_configured_source(tmp_path: Path):
    from market_research.cli import main

    config = tmp_path / "config.toml"
    config.write_text(f'output_root = "{tmp_path / "outputs"}"\n', encoding="utf-8")

    assert main(["validate", "--config", str(config)]) == 0


def test_microcap_report_command_writes_reconstruction_outputs(tmp_path: Path):
    from market_research.cli import main

    a_share = tmp_path / "a_share"
    a_share.mkdir()
    pd.DataFrame(
        {
            "trade_date": ["2026-01-01", "2026-01-02"],
            "adj_close": [10.0, 11.0],
            "amount": [1000.0, 1100.0],
            "total_mv": [5000.0, 5000.0],
            "is_st": [False, False],
            "is_suspended": [False, False],
        }
    ).to_parquet(a_share / "000001.SZ.parquet")
    config = tmp_path / "config.toml"
    output = tmp_path / "outputs"
    config.write_text(
        f'output_root = "{output}"\n\n[sources]\na_share_root = "{a_share}"\n',
        encoding="utf-8",
    )

    assert main(["report", "microcap", "--config", str(config)]) == 0
    assert (output / "microcap_nav.csv").exists()
    assert (output / "microcap_summary.json").exists()
    assert len(pd.read_csv(output / "microcap_nav.csv")) == 1
