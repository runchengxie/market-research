from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..contracts import PanelMetadata, normalize_panel


def build_hk_panel(
    daily_root: Path,
    valuation_root: Path,
    instruments_path: Path,
    as_of: str | None = None,
    fx_rate: float | None = 7.8,
) -> tuple[pd.DataFrame, PanelMetadata]:
    instruments = _read_instruments(instruments_path)
    eligible_symbols = set(
        instruments.loc[
            instruments["status"].eq("Active")
            & ~instruments["type"].astype("string").str.contains("ETF", case=False, na=False),
            "symbol",
        ]
    )
    rows: list[pd.DataFrame] = []
    for daily_path in sorted(Path(daily_root).rglob("*.parquet")):
        symbol = daily_path.stem
        if symbol not in eligible_symbols:
            continue
        valuation_path = Path(valuation_root) / daily_path.name
        if not valuation_path.exists():
            matches = list(Path(valuation_root).rglob(daily_path.name))
            if not matches:
                continue
            valuation_path = matches[0]
        daily = pd.read_parquet(daily_path)
        valuation = pd.read_parquet(valuation_path)
        required_daily = {"trade_date", "total_turnover"}
        required_valuation = {"trade_date", "hk_total_market_val"}
        if not required_daily.issubset(daily.columns) or not required_valuation.issubset(valuation.columns):
            continue
        joined = daily[list(required_daily)].merge(valuation[list(required_valuation)], on="trade_date")
        joined["date"] = pd.to_datetime(joined["trade_date"], errors="coerce").dt.date
        joined["total_turnover"] = pd.to_numeric(joined["total_turnover"], errors="coerce")
        joined["hk_total_market_val"] = pd.to_numeric(joined["hk_total_market_val"], errors="coerce")
        eligible = joined.loc[
            joined["date"].notna()
            & (joined["total_turnover"] > 0)
            & (joined["hk_total_market_val"] > 0)
        ].copy()
        if as_of is not None:
            eligible = eligible.loc[eligible["date"] <= pd.Timestamp(as_of).date()]
        if eligible.empty:
            continue
        rows.append(
            pd.DataFrame(
                {
                    "market": "hk",
                    "symbol": symbol,
                    "date": eligible["date"],
                    "close": pd.NA,
                    "volume": pd.NA,
                    "turnover": eligible["total_turnover"],
                    "market_cap": eligible["hk_total_market_val"],
                    "currency": "HKD",
                    "is_tradable": True,
                    "is_suspended": False,
                    "source": str(daily_path),
                }
            )
        )
    panel = pd.concat(rows, ignore_index=True) if rows else _empty_panel()
    metadata = _metadata(panel, "RQData Hong Kong daily/valuation", as_of, fx_rate)
    return normalize_panel(panel, metadata)


def _read_instruments(path: Path) -> pd.DataFrame:
    if path.is_file():
        return pd.read_parquet(path)
    files = sorted(path.rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"no HK instrument parquet files under {path}")
    return pd.concat([pd.read_parquet(file) for file in files], ignore_index=True)


def _empty_panel() -> pd.DataFrame:
    return pd.DataFrame(columns=["market", "symbol", "date", "close", "volume", "turnover", "market_cap", "currency", "is_tradable", "is_suspended", "source"])


def _metadata(panel: pd.DataFrame, source: str, as_of: str | None, fx_rate: float | None) -> PanelMetadata:
    start = str(panel["date"].min()) if not panel.empty else None
    end = str(panel["date"].max()) if not panel.empty else None
    return PanelMetadata(
        source=source, as_of=as_of or end or "", currency="HKD",
        universe_filter="Active non-ETF; positive total_turnover and market value",
        fx_method="native HKD" if fx_rate is None else f"reference FX divisor {fx_rate:g}",
        feature_lag=1, coverage_start=start, coverage_end=end,
        calendar_mode="observed_daily", quality_status="verified" if not panel.empty else "incomplete",
    )
