import pandas as pd
import pytest


def _stats(values: list[float], dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": dates,
            "rank_count": [10] * len(dates),
            "eligible_count": [100] * len(dates),
            "selected_count": [10] * len(dates),
            "turnover_sum": values,
            "turnover_mean": values,
            "turnover_median": values,
            "market_cap_median": [1_000.0] * len(dates),
        }
    )


def test_build_overlap_audit_quantifies_relative_turnover_difference():
    from market_research.smallcap_turnover_audit import build_overlap_audit

    result = build_overlap_audit(
        _stats([100.0, 200.0], ["2015-01-05", "2015-01-06"]),
        _stats([105.0, 160.0], ["2015-01-05", "2015-01-06"]),
    )

    row = result.iloc[0]
    assert row["rank_count"] == 10
    assert row["common_days"] == 2
    assert row["within_10pct_ratio"] == pytest.approx(0.5)
    assert row["mean_abs_relative_diff_turnover_median"] == pytest.approx(0.125)
    assert row["quality_note"] == "historical eligibility is incomplete"
