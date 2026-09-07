from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..contracts import PanelMetadata, normalize_panel


def build_us_panel(source_path: Path, as_of: str | None = None) -> tuple[pd.DataFrame, PanelMetadata]:
    source = _resolve_source(Path(source_path))
    frame = pd.read_csv(source, sep=";", dtype=str)
    for column in ("Close", "Volume", "Shares Outstanding"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["date"] = pd.to_datetime(frame["Date"], errors="coerce").dt.date
    eligible = frame.loc[
        frame["date"].notna()
        & (frame["Close"] >= 1)
        & (frame["Volume"] > 0)
        & (frame["Shares Outstanding"] > 0)
    ].copy()
    if as_of is not None:
        eligible = eligible.loc[eligible["date"] <= pd.Timestamp(as_of).date()]
    panel = pd.DataFrame(
        {
            "market": "us",
            "symbol": eligible["Ticker"],
            "date": eligible["date"],
            "close": eligible["Close"],
            "volume": eligible["Volume"],
            "turnover": eligible["Close"] * eligible["Volume"],
            "market_cap": eligible["Close"] * eligible["Shares Outstanding"],
            "currency": "USD",
            "is_tradable": True,
            "is_suspended": False,
            "source": str(source),
        }
    )
    metadata = PanelMetadata(
        source="SimFin USA shareprices", as_of=as_of or (str(panel["date"].max()) if not panel.empty else ""),
        currency="USD", universe_filter="Close >= 1; positive volume and shares outstanding",
        fx_method="native USD", feature_lag=1,
        coverage_start=str(panel["date"].min()) if not panel.empty else None,
        coverage_end=str(panel["date"].max()) if not panel.empty else None,
        calendar_mode="observed_daily", quality_status="verified" if not panel.empty else "incomplete",
    )
    return normalize_panel(panel, metadata)


def _resolve_source(path: Path) -> Path:
    if path.is_file():
        return path
    candidates = sorted(path.rglob("us-shareprices-daily.csv")) + sorted(path.rglob("*.csv"))
    if not candidates:
        raise FileNotFoundError(f"no SimFin CSV files under {path}")
    return candidates[0]
