from __future__ import annotations

import pandas as pd


def profile_panel(frame: pd.DataFrame) -> dict[str, object]:
    turnover = pd.to_numeric(frame["turnover"], errors="coerce")
    return {
        "rows": int(len(frame)),
        "symbols": int(frame["symbol"].nunique(dropna=True)),
        "coverage_start": str(frame["date"].min()) if len(frame) else None,
        "coverage_end": str(frame["date"].max()) if len(frame) else None,
        "missing_turnover_rows": int(turnover.isna().sum()),
        "zero_turnover_rows": int((turnover == 0).sum()),
        "missing_market_cap_rows": int(pd.to_numeric(frame["market_cap"], errors="coerce").isna().sum()),
        "non_tradable_rows": int((~frame["is_tradable"].astype(bool)).sum()),
    }
