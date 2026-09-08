import pandas as pd
import pytest


def _nav() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2022-01-03", "2022-12-30", "2023-12-29", "2024-12-31"],
            "nav": [1.0, 1.2, 0.9, 1.8],
        }
    )


def test_annual_returns_uses_last_nav_of_each_year():
    from market_research.microcap import calculate_annual_returns

    result = calculate_annual_returns(_nav())

    assert result.to_dict("records") == [
        {"year": 2022, "return": pytest.approx(0.2), "nav": 1.2},
        {"year": 2023, "return": pytest.approx(-0.25), "nav": 0.9},
        {"year": 2024, "return": pytest.approx(1.0), "nav": 1.8},
    ]


def test_rolling_cagr_and_drawdown_preserve_legacy_windows():
    from market_research.microcap import calculate_rolling_cagr, calculate_rolling_drawdown

    cagr = calculate_rolling_cagr(_nav(), windows=(1, 2))
    drawdown = calculate_rolling_drawdown(_nav(), windows=(2,))

    assert list(cagr["window_years"]) == [1, 1, 2]
    assert cagr.iloc[-1]["cagr"] == pytest.approx(0.2247448714)
    assert drawdown.loc[drawdown["as_of"].eq("2023-12-29"), "max_drawdown"].iloc[0] == pytest.approx(-0.25)
    assert drawdown.iloc[-1]["frequency"] == "annual_reference"


def test_write_microcap_snapshot_emits_legacy_public_files(tmp_path):
    from market_research.microcap import write_microcap_snapshot

    write_microcap_snapshot(_nav(), tmp_path, "fixture")

    assert {path.name for path in tmp_path.iterdir()} == {
        "annual_returns.csv",
        "rolling_cagr.csv",
        "rolling_drawdown.csv",
        "nav.csv",
        "summary.json",
    }
    assert pd.read_csv(tmp_path / "nav.csv")["source"].tolist() == ["fixture"] * 4
