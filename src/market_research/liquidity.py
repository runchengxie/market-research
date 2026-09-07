from __future__ import annotations

import pandas as pd


def add_lagged_liquidity(
    panel: pd.DataFrame, windows: tuple[int, ...] = (20, 60)
) -> pd.DataFrame:
    result = panel.copy()
    result["date"] = pd.to_datetime(result["date"]).dt.date
    result = result.sort_values(["market", "symbol", "date"], kind="stable").reset_index(drop=True)
    result["_usable_turnover"] = pd.to_numeric(result["turnover"], errors="coerce").where(
        result["is_tradable"].astype(bool)
    )
    grouped = result.groupby(["market", "symbol"], sort=False)["_usable_turnover"]
    for window in windows:
        result[f"adv{window}"] = grouped.transform(
            lambda values: values.shift(1).rolling(window, min_periods=window).mean()
        )
        result[f"medadv{window}"] = grouped.transform(
            lambda values: values.shift(1).rolling(window, min_periods=window).median()
        )
    return result.drop(columns="_usable_turnover")
