from __future__ import annotations

import pandas as pd


def analyze_tail_monotonicity(
    quantile_returns: pd.DataFrame,
    *,
    direction: str = "ascending",
    tail_quantiles: int = 1,
) -> dict[str, object]:
    if direction not in {"ascending", "descending"} or tail_quantiles < 1:
        raise ValueError("invalid direction or tail_quantiles")
    if quantile_returns.empty:
        return {"monotonicity_score": 0.0, "tail_spread": 0.0, "observations": 0}
    curve = quantile_returns.groupby("bucket")["mean_forward_return"].mean().sort_index()
    if direction == "descending":
        curve = curve.sort_index(ascending=False)
    adjacent = curve.diff().dropna()
    score = float((adjacent >= 0).mean()) if len(adjacent) else 0.0
    low = curve.iloc[:tail_quantiles].mean()
    high = curve.iloc[-tail_quantiles:].mean()
    return {
        "monotonicity_score": score,
        "tail_spread": float(low - high),
        "observations": int(quantile_returns["formation_date"].nunique()),
        "quantiles": int(curve.size),
        "direction": direction,
    }


def summarize_market_factor_evidence(
    quantile_returns: pd.DataFrame, factor_name: str, metadata: dict[str, object] | None = None
) -> dict[str, object]:
    summary = analyze_tail_monotonicity(quantile_returns)
    summary.update({"factor": factor_name, "evidence_status": "derived"})
    if metadata:
        summary["provenance"] = metadata
    return summary
