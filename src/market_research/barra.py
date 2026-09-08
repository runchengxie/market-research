from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def load_barra_summary(path: Path) -> dict[str, object]:
    root = Path(path)
    if not root.is_dir():
        raise FileNotFoundError(root)
    manifest = _read_json(root / "manifest.json")
    meta = _read_json(root / "meta.json")
    factor_summary = _read_json(root / "factor_summary.json")
    size = next((row for row in factor_summary if row.get("factor") == "size"), None)
    if size is None:
        raise ValueError("Barra result does not contain a size factor")
    return {
        "source_root": str(root),
        "schema_version": manifest.get("schema_version"),
        "generated_at": manifest.get("generated_at"),
        "factor_count": meta.get("factor_count", len(meta.get("factors", []))),
        "factors": meta.get("factors", []),
        "coverage_start": meta.get("data_start"),
        "coverage_end": meta.get("data_end"),
        "rebalance_frequency": meta.get("rebalance_frequency"),
        "quantiles": meta.get("quantiles"),
        "size_factor": size,
    }


def summarize_barra_factor_file(path: Path) -> dict[str, object]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    frame = pd.read_csv(source)
    if "trade_date" not in frame.columns or len(frame.columns) != 2:
        raise ValueError("factor daily file must contain trade_date and one factor column")
    factor = next(column for column in frame.columns if column != "trade_date")
    values = pd.to_numeric(frame[factor], errors="coerce")
    dates = pd.to_datetime(frame["trade_date"], errors="coerce")
    valid = values.notna() & dates.notna()
    if not valid.any():
        raise ValueError(f"factor file has no valid observations: {source}")
    return {
        "factor": factor.removeprefix("factor_").removesuffix("_daily"),
        "observations": int(valid.sum()),
        "coverage_start": dates.loc[valid].min().date().isoformat(),
        "coverage_end": dates.loc[valid].max().date().isoformat(),
        "mean_return": float(values.loc[valid].mean()),
    }


def analyze_size_monotonicity(
    panel: pd.DataFrame, quantiles: int = 10, holding_period: int = 1
) -> tuple[pd.DataFrame, dict[str, object]]:
    if quantiles < 2:
        raise ValueError("quantiles must be at least 2")
    if holding_period < 1:
        raise ValueError("holding_period must be positive")
    required = {"symbol", "date", "adj_close", "market_cap"}
    missing = required.difference(panel.columns)
    if missing:
        raise ValueError("missing panel columns: " + ",".join(sorted(missing)))

    frame = panel.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame["market_cap"] = pd.to_numeric(frame["market_cap"], errors="coerce")
    for column in ("is_st", "is_suspended", "is_tradable"):
        if column not in frame:
            frame[column] = False if column != "is_tradable" else True
    dates = sorted(frame["date"].dropna().unique())
    future_dates = {date: dates[index + holding_period] for index, date in enumerate(dates[:-holding_period])}
    frame = frame.sort_values(["symbol", "date"], kind="stable")
    frame["future_date"] = frame.groupby("symbol")["date"].shift(-holding_period)
    frame["future_adj_close"] = frame.groupby("symbol")["adj_close"].shift(-holding_period)
    frame["expected_future_date"] = frame["date"].map(future_dates)
    eligible = frame.loc[
        frame["date"].notna()
        & frame["market_cap"].gt(0)
        & frame["adj_close"].gt(0)
        & frame["is_tradable"].astype(bool)
        & ~frame["is_st"].astype(bool)
        & ~frame["is_suspended"].astype(bool)
        & frame["future_date"].eq(frame["expected_future_date"])
        & frame["future_adj_close"].gt(0)
    ].copy()
    eligible["forward_return"] = eligible["future_adj_close"] / eligible["adj_close"] - 1
    eligible["bucket"] = (
        eligible.groupby("date")["market_cap"]
        .rank(method="first", ascending=True, pct=True)
        .mul(quantiles)
        .apply(lambda value: min(quantiles, max(1, int(np.ceil(value)))))
    )
    result = (
        eligible.groupby(["date", "bucket"], as_index=False)
        .agg(
            mean_forward_return=("forward_return", "mean"),
            median_forward_return=("forward_return", "median"),
            count=("forward_return", "size"),
        )
        .rename(columns={"date": "formation_date"})
    )
    result["bucket"] = result["bucket"].astype(int)
    result["bucket_label"] = result["bucket"].map(lambda bucket: f"Q{bucket}")
    curve = result.groupby("bucket")["mean_forward_return"].mean().sort_index()
    adjacent = curve.diff().dropna()
    score = float((adjacent <= 0).mean()) if not adjacent.empty else 0.0
    summary = {
        "quantiles": quantiles,
        "holding_period": holding_period,
        "monotonicity_score": score,
        "tail_spread": float(curve.iloc[0] - curve.iloc[-1]) if len(curve) >= 2 else 0.0,
        "coverage_start": result["formation_date"].min().date().isoformat() if not result.empty else None,
        "coverage_end": result["formation_date"].max().date().isoformat() if not result.empty else None,
        "formation_dates": int(result["formation_date"].nunique()),
        "eligible_rows": int(len(eligible)),
        "excluded_rows": int(len(frame) - len(eligible)),
    }
    return result.sort_values(["bucket", "formation_date"]).reset_index(drop=True), summary


def _read_json(path: Path) -> dict[str, object] | list[dict[str, object]]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
