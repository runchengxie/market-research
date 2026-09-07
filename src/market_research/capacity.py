from __future__ import annotations

import pandas as pd


def build_instrument_capacity(
    panel: pd.DataFrame,
    participation_rates: tuple[float, ...] = (0.01, 0.03, 0.05, 0.10),
    horizons: tuple[int, ...] = (1, 5, 10),
    liquidity_column: str = "medadv20",
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for participation_rate in participation_rates:
        if participation_rate <= 0 or participation_rate > 1:
            raise ValueError("participation rates must be in (0, 1]")
        for horizon in horizons:
            if horizon <= 0:
                raise ValueError("horizons must be positive")
            result = panel.copy()
            liquidity = pd.to_numeric(result[liquidity_column], errors="coerce")
            tradable = result["is_tradable"].astype(bool)
            quality = pd.Series("ok", index=result.index, dtype="string")
            quality.loc[~tradable] = "non_tradable"
            quality.loc[tradable & liquidity.isna()] = "missing_liquidity"
            quality.loc[tradable & liquidity.notna() & (liquidity <= 0)] = "zero_liquidity"
            result["participation_rate"] = participation_rate
            result["horizon_days"] = horizon
            result["liquidity"] = liquidity
            result["daily_capacity"] = (liquidity * participation_rate).where(quality == "ok", 0.0)
            result["horizon_capacity"] = result["daily_capacity"] * horizon
            result["capacity_quality"] = quality
            rows.append(result)
    return pd.concat(rows, ignore_index=True) if rows else panel.iloc[0:0].copy()


def build_capacity_surface(
    panel: pd.DataFrame,
    participation_rates: tuple[float, ...] = (0.01, 0.03, 0.05, 0.10),
    horizons: tuple[int, ...] = (1, 5, 10),
    liquidity_column: str = "medadv20",
) -> pd.DataFrame:
    instrument = build_instrument_capacity(panel, participation_rates, horizons, liquidity_column)
    instrument = instrument.copy()
    instrument["market_cap_bucket"] = instrument["market_cap"].map(_market_cap_bucket)
    group_columns = ["market", "date", "market_cap_bucket", "participation_rate", "horizon_days"]
    return (
        instrument.groupby(group_columns, dropna=False, as_index=False)
        .agg(
            instrument_count=("symbol", "size"),
            tradable_count=("capacity_quality", lambda values: int((values == "ok").sum())),
            gross_capacity=("horizon_capacity", "sum"),
            p05_capacity=("horizon_capacity", lambda values: values.quantile(0.05)),
            median_capacity=("horizon_capacity", "median"),
            p95_capacity=("horizon_capacity", lambda values: values.quantile(0.95)),
        )
    )


def _market_cap_bucket(value: object) -> str:
    if pd.isna(value):
        return "unknown"
    value = float(value)
    if value < 1e7:
        return "<1e7"
    if value < 1e8:
        return "1e7-1e8"
    if value < 1e9:
        return "1e8-1e9"
    if value < 1e10:
        return "1e9-1e10"
    return ">=1e10"
