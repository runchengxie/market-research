from __future__ import annotations

import pandas as pd


def build_quantile_returns(
    panel: pd.DataFrame,
    factor_column: str,
    quantiles: int = 10,
    holding_period: int = 1,
    date_column: str = "date",
    return_column: str = "adj_close",
) -> pd.DataFrame:
    """Build lag-safe equal-weight factor quantile returns.

    Factor values are ranked on formation date and returns start on the next
    available panel date. This is deliberately a market-evidence primitive;
    it does not calculate IC, decay, alpha scores, or strategy weights.
    """
    if quantiles < 2 or holding_period < 1:
        raise ValueError("quantiles must be >= 2 and holding_period must be positive")
    required = {"symbol", date_column, factor_column, return_column}
    missing = required.difference(panel.columns)
    if missing:
        raise ValueError("missing panel columns: " + ", ".join(sorted(missing)))
    frame = panel.copy()
    frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
    frame[return_column] = pd.to_numeric(frame[return_column], errors="coerce")
    frame[factor_column] = pd.to_numeric(frame[factor_column], errors="coerce")
    frame = frame.sort_values(["symbol", date_column], kind="stable")
    dates = sorted(frame[date_column].dropna().unique())
    target_dates = {
        date: dates[i + holding_period]
        for i, date in enumerate(dates[:-holding_period])
    }
    frame["future_date"] = frame.groupby("symbol")[date_column].shift(-holding_period)
    frame["future_price"] = frame.groupby("symbol")[return_column].shift(-holding_period)
    for column, default in (("is_tradable", True), ("is_st", False), ("is_suspended", False)):
        if column not in frame:
            frame[column] = default
    eligible = frame.loc[
        frame[date_column].notna()
        & frame[factor_column].notna()
        & frame[return_column].gt(0)
        & frame["future_date"].eq(frame[date_column].map(target_dates))
        & frame["future_price"].gt(0)
        & frame["is_tradable"].astype(bool)
        & ~frame["is_st"].astype(bool)
        & ~frame["is_suspended"].astype(bool)
    ].copy()
    eligible["forward_return"] = eligible["future_price"] / eligible[return_column] - 1.0
    eligible["bucket"] = (
        eligible.groupby(date_column)[factor_column]
        .rank(method="first", ascending=True, pct=True)
        .mul(quantiles)
        .clip(1, quantiles)
        .astype(int)
    )
    result = (
        eligible.groupby([date_column, "bucket"], as_index=False)
        .agg(
            mean_forward_return=("forward_return", "mean"),
            median_forward_return=("forward_return", "median"),
            count=("forward_return", "size"),
        )
        .rename(columns={date_column: "formation_date"})
    )
    result["bucket_label"] = result["bucket"].map(lambda value: f"Q{value}")
    return result.sort_values(["formation_date", "bucket"]).reset_index(drop=True)
