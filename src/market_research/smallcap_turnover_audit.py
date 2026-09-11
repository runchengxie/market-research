from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = {"date", "rank_count", "selected_count", "turnover_median"}


def build_overlap_audit(clean_daily: pd.DataFrame, historical_daily: pd.DataFrame) -> pd.DataFrame:
    """Compare clean 2015+ and incomplete historical turnover summaries."""
    for label, frame in (("clean_daily", clean_daily), ("historical_daily", historical_daily)):
        missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
        if missing:
            raise ValueError(f"{label} is missing columns: " + ",".join(missing))

    clean = clean_daily.copy()
    historical = historical_daily.copy()
    for frame in (clean, historical):
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["rank_count"] = pd.to_numeric(frame["rank_count"], errors="coerce")
        frame["selected_count"] = pd.to_numeric(frame["selected_count"], errors="coerce")
        frame["turnover_median"] = pd.to_numeric(frame["turnover_median"], errors="coerce")

    merged = clean[["date", "rank_count", "selected_count", "turnover_median"]].merge(
        historical[["date", "rank_count", "selected_count", "turnover_median"]],
        on=["date", "rank_count"],
        suffixes=("_clean", "_historical"),
        how="inner",
    )
    rows: list[dict[str, object]] = []
    rank_counts = sorted(
        set(clean["rank_count"].dropna().astype(int))
        | set(historical["rank_count"].dropna().astype(int))
    )
    for rank_count in rank_counts:
        subset = merged.loc[merged["rank_count"].eq(rank_count)].copy()
        clean_values = subset["turnover_median_clean"]
        relative = (
            (subset["turnover_median_historical"] - clean_values).abs()
            / clean_values.where(clean_values.ne(0))
        ).dropna()
        rows.append(
            {
                "rank_count": rank_count,
                "common_days": int(len(subset)),
                "common_start": subset["date"].min().date().isoformat() if not subset.empty else None,
                "common_end": subset["date"].max().date().isoformat() if not subset.empty else None,
                "mean_abs_relative_diff_turnover_median": float(relative.mean()) if not relative.empty else None,
                "p90_abs_relative_diff_turnover_median": float(relative.quantile(0.90)) if not relative.empty else None,
                "within_5pct_ratio": float(relative.le(0.05).mean()) if not relative.empty else None,
                "within_10pct_ratio": float(relative.le(0.10).mean()) if not relative.empty else None,
                "within_25pct_ratio": float(relative.le(0.25).mean()) if not relative.empty else None,
                "mean_selected_count_diff": float(
                    (subset["selected_count_historical"] - subset["selected_count_clean"]).mean()
                ) if not subset.empty else None,
                "quality_note": "historical eligibility is incomplete",
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "rank_count", "common_days", "common_start", "common_end",
            "mean_abs_relative_diff_turnover_median", "p90_abs_relative_diff_turnover_median",
            "within_5pct_ratio", "within_10pct_ratio", "within_25pct_ratio",
            "mean_selected_count_diff", "quality_note",
        ],
    )
