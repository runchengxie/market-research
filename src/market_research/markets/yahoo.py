"""Optional Yahoo Finance share-count source for exploratory JP research.

Yahoo reports share-count change events rather than a complete daily panel.
This module converts those events into a dated sidecar that the JP adapter can
join to the local J-Quants daily bars.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Lock
from typing import Iterable

import pandas as pd


def symbols_pending_download(symbols: Iterable[str], completed: set[str]) -> list[str]:
    """Return stable, de-duplicated symbols that do not have a checkpoint."""
    return [symbol for symbol in dict.fromkeys(str(item).zfill(5) for item in symbols) if symbol not in completed]


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
    parts_dir: Path | None = None,
    delay_seconds: float = 0.0,
    error_path: Path | None = None,
    workers: int = 1,
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
    if workers < 1:
        raise ValueError("workers must be at least 1")

    import time

    parts = Path(parts_dir) if parts_dir else None
    if parts:
        parts.mkdir(parents=True, exist_ok=True)
    completed = {path.stem for path in parts.glob("*.parquet")} if parts else set()
    rows: list[pd.DataFrame] = []
    groups = daily_panel.groupby("symbol", sort=True)
    pending = symbols_pending_download(groups.groups, completed)
    error_lock = Lock()

    def download_one(code: str) -> pd.DataFrame:
        group = groups.get_group(code)
        try:
            ticker = yf.Ticker(jp_code_to_yahoo_symbol(code))
            events = ticker.get_shares_full(start=start, end=end)
            if events is None or len(events) == 0:
                result = pd.DataFrame(columns=["date", "symbol", "shares_outstanding"])
            else:
                result = build_daily_shares_sidecar(code, events, pd.to_datetime(group["date"]).dt.date)
            if parts:
                result.to_parquet(parts / f"{code}.parquet", index=False)
            return result
        except Exception as error:  # pragma: no cover - depends on Yahoo response
            if error_path:
                with error_lock:
                    with Path(error_path).open("a", encoding="utf-8") as handle:
                        handle.write(f"{code}\t{type(error).__name__}\t{error}\n")
            return pd.DataFrame(columns=["date", "symbol", "shares_outstanding"])
        finally:
            if delay_seconds > 0:
                time.sleep(delay_seconds)

    if workers == 1:
        rows.extend(download_one(code) for code in pending)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            rows.extend(executor.map(download_one, pending))

    if parts:
        rows = [pd.read_parquet(path) for path in sorted(parts.glob("*.parquet"))]

    result = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["date", "symbol", "shares_outstanding"])
    result["date"] = pd.to_datetime(result["date"]).dt.date
    result.to_parquet(output_path, index=False)
    return result
