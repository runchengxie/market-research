from __future__ import annotations

from pathlib import Path

import pandas as pd

MARKETS = ("US", "HK", "UK", "AU", "CA", "SG")
LOCAL_CURRENCY = {"US": "USD", "HK": "HKD", "UK": "GBP", "AU": "AUD", "CA": "CAD", "SG": "SGD"}


def _read(path: Path, required: set[str]) -> pd.DataFrame:
    if not path.is_file():
        raise ValueError(f"input file does not exist: {path}")
    frame = pd.read_csv(path)
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"input missing columns: {missing}")
    return frame


def load_daily_asset(path: Path, market: str) -> pd.DataFrame:
    if market not in MARKETS:
        raise ValueError(f"unknown market: {market}")
    result = _read(path, {"date", "close", "volume"})[["date", "close", "volume"]].copy()
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.normalize()
    result["close"] = pd.to_numeric(result["close"], errors="raise")
    result["volume"] = pd.to_numeric(result["volume"], errors="raise")
    if result["date"].duplicated().any() or (result["close"] <= 0).any() or (result["volume"] < 0).any():
        raise ValueError(f"invalid or duplicate asset observations: {path}")
    result["market"] = market
    result["currency"] = LOCAL_CURRENCY[market]
    return result.sort_values("date").reset_index(drop=True)


def load_fx_series(path: Path, currency: str) -> pd.DataFrame:
    result = _read(path, {"date", "usd_per_local"})[["date", "usd_per_local"]].copy()
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.normalize()
    result["usd_per_local"] = pd.to_numeric(result["usd_per_local"], errors="raise")
    if result["date"].duplicated().any() or (result["usd_per_local"] <= 0).any():
        raise ValueError(f"invalid or duplicate FX observations: {path}")
    result["currency"] = currency
    return result.sort_values("date").reset_index(drop=True)


def load_distributions(path: Path, market: str, currency: str) -> pd.DataFrame:
    result = _read(path, {"date", "cash_per_share", "currency"})[["date", "cash_per_share", "currency"]].copy()
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.normalize()
    result["cash_per_share"] = pd.to_numeric(result["cash_per_share"], errors="raise")
    if (result["cash_per_share"] < 0).any() or not result["currency"].eq(currency).all():
        raise ValueError(f"invalid distribution currency/value for {market}")
    result["market"] = market
    return result.sort_values("date").reset_index(drop=True)


def validate_common_history(assets: dict[str, pd.DataFrame], fx: dict[str, pd.DataFrame], minimum_months: int = 24) -> dict[str, object]:
    if set(assets) != set(MARKETS):
        raise ValueError("assets must contain exactly the six configured markets")
    all_inputs = [*assets.values(), *fx.values()]
    start = max(frame["date"].min() for frame in all_inputs)
    end = min(frame["date"].max() for frame in all_inputs)
    months = int((end.to_period("M") - start.to_period("M")).n) + 1
    if months < minimum_months:
        raise ValueError(f"common history has {months} months, requires {minimum_months}")
    return {"common_start": start.date().isoformat(), "common_end": end.date().isoformat(), "common_months": months}
