"""Optional Yahoo Finance share-count source for exploratory JP research.

Yahoo reports share-count change events rather than a complete daily panel.
This module converts those events into a dated sidecar that the JP adapter can
join to the local J-Quants daily bars.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd


def jp_code_to_yahoo_symbol(code: object) -> str:
    """Convert a JPX five-character code to Yahoo's four-digit ``.T`` code."""
    text = str(code).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if len(text) == 4:
        return f"{text}.T"
    return f"{text.zfill(5)[:4]}.T"


def build_daily_shares_sidecar(
    code: object,
    share_events: pd.Series,
    trading_dates: Iterable[date],
) -> pd.DataFrame:
    """Forward-fill Yahoo share-count events onto the requested trading dates."""
    dates = pd.DataFrame({"date": pd.to_datetime(list(trading_dates), utc=True).tz_localize(None).astype("datetime64[ns]")})
    if dates.empty:
        return pd.DataFrame(columns=["date", "symbol", "shares_outstanding"])

    event_dates = pd.to_datetime(share_events.index, utc=True).tz_localize(None).astype("datetime64[ns]")
    events = pd.DataFrame({"event_date": event_dates, "shares_outstanding": pd.to_numeric(share_events.values, errors="coerce")})
    events = events.dropna(subset=["event_date", "shares_outstanding"]).sort_values("event_date")
    if events.empty:
        return pd.DataFrame(columns=["date", "symbol", "shares_outstanding"])

    result = pd.merge_asof(
        dates.sort_values("date"),
        events,
        left_on="date",
        right_on="event_date",
        direction="backward",
    )
    result["symbol"] = str(code).strip().zfill(5)
    return result[["date", "symbol", "shares_outstanding"]].dropna(subset=["shares_outstanding"])


def build_yfinance_shares_sidecar(
    daily_panel: pd.DataFrame,
    output_path: Path,
    *,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Download Yahoo share-count events for symbols in a JP daily panel.

    ``yfinance`` is intentionally an optional dependency. The input panel is
    used for the exact observed trading dates, so no synthetic calendar is
    introduced. Failed symbols are skipped and reported by the caller through
    the returned coverage table.
    """
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - exercised in CLI usage
        raise RuntimeError("Install the optional yahoo extra to use this source") from exc

    required = {"symbol", "date"}
    if not required.issubset(daily_panel.columns):
        raise ValueError("daily_panel requires symbol and date columns")

    rows: list[pd.DataFrame] = []
    for code, group in daily_panel.groupby("symbol", sort=True):
        ticker = yf.Ticker(jp_code_to_yahoo_symbol(code))
        events = ticker.get_shares_full(start=start, end=end)
        if events is None or len(events) == 0:
            continue
        rows.append(build_daily_shares_sidecar(code, events, pd.to_datetime(group["date"]).dt.date))

    result = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["date", "symbol", "shares_outstanding"])
    result["date"] = pd.to_datetime(result["date"]).dt.date
    result.to_parquet(output_path, index=False)
    return result
