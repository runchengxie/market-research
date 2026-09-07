from pathlib import Path


def test_cli_help_returns_success():
    from market_research.cli import main

    assert main(["--help"]) == 0


def test_config_inspect_prints_resolved_output_root(tmp_path: Path, capsys):
    from market_research.cli import main

    assert main(["config", "inspect", "--output-root", str(tmp_path)]) == 0
    assert str(tmp_path) in capsys.readouterr().out
