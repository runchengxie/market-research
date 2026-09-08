import json
from pathlib import Path

import pandas as pd
import pytest


def test_load_barra_summary_exposes_manifest_and_size_factor(tmp_path: Path):
    (tmp_path / "manifest.json").write_text(
        json.dumps({"schema_version": "research.style-factors.v1", "generated_at": "2026-09-05"}),
        encoding="utf-8",
    )
    (tmp_path / "meta.json").write_text(
        json.dumps({"factor_count": 19, "factors": ["size", "value"]}), encoding="utf-8"
    )
    (tmp_path / "factor_summary.json").write_text(
        json.dumps([{"factor": "size", "geometric_annual_ret": -22.16, "sharpe": -1.74}]),
        encoding="utf-8",
    )

    from market_research.barra import load_barra_summary

    result = load_barra_summary(tmp_path)
    assert result["factor_count"] == 19
    assert result["size_factor"]["geometric_annual_ret"] == -22.16
    assert result["schema_version"] == "research.style-factors.v1"


def test_load_barra_summary_rejects_missing_result_root(tmp_path: Path):
    from market_research.barra import load_barra_summary

    with pytest.raises(FileNotFoundError):
        load_barra_summary(tmp_path / "missing")


def test_summarize_barra_factor_file_reads_daily_factor_stats(tmp_path: Path):
    path = tmp_path / "factor_size_daily.csv"
    pd.DataFrame({"trade_date": ["2024-01-31", "2024-02-29"], "size": [-0.1, 0.2]}).to_csv(path, index=False)

    from market_research.barra import summarize_barra_factor_file

    result = summarize_barra_factor_file(path)
    assert result == {
        "factor": "size",
        "observations": 2,
        "coverage_start": "2024-01-31",
        "coverage_end": "2024-02-29",
        "mean_return": 0.05,
    }


def _panel() -> pd.DataFrame:
    rows = []
    returns = [0.10, 0.08, 0.06, 0.04]
    for date, prices in [
        ("2024-01-01", [100.0] * 4),
        ("2024-01-02", [100.0 * (1 + x) for x in returns]),
        ("2024-01-03", [100.0 * (1 + x) * (1 + x) for x in returns]),
    ]:
        for i, price in enumerate(prices):
            rows.append(
                {
                    "market": "a_share",
                    "symbol": f"S{i}",
                    "date": date,
                    "adj_close": price,
                    "market_cap": float(i + 1),
                    "is_suspended": False,
                    "is_tradable": True,
                }
            )
    return pd.DataFrame(rows)


def test_analyze_size_monotonicity_scores_small_to_large_order():
    from market_research.barra import analyze_size_monotonicity

    panel = _panel()
    result, summary = analyze_size_monotonicity(panel, quantiles=4)

    assert result["bucket"].unique().tolist() == [1, 2, 3, 4]
    assert result.groupby("bucket")["mean_forward_return"].mean().tolist() == pytest.approx(
        [0.10, 0.08, 0.06, 0.04]
    )
    assert summary["monotonicity_score"] == 1.0
    assert summary["tail_spread"] == pytest.approx(0.06)


def test_analyze_size_monotonicity_keeps_quantile_buckets_balanced():
    from market_research.barra import analyze_size_monotonicity

    panel = _panel().loc[_panel()["date"].isin(["2024-01-01", "2024-01-02"])].copy()
    result, _ = analyze_size_monotonicity(panel, quantiles=2)

    assert result.groupby(["formation_date", "bucket"], observed=True)["count"].sum().tolist() == [2, 2]


def test_analyze_size_monotonicity_excludes_st_and_suspended_rows():
    from market_research.barra import analyze_size_monotonicity

    panel = _panel()
    panel["is_st"] = False
    panel.loc[panel["symbol"] == "S0", "is_st"] = True
    panel.loc[panel["symbol"] == "S1", "is_suspended"] = True
    panel["date"] = pd.to_datetime(panel["date"])

    result, summary = analyze_size_monotonicity(panel, quantiles=2)

    assert result["count"].sum() == 4
    assert summary["excluded_rows"] == 8
