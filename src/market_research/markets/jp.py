from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..contracts import PanelMetadata, normalize_panel


def discover_jp_daily_files(data_root: Path) -> list[Path]:
    return sorted(Path(data_root).rglob("equities_bars_daily_*.parquet"))


def build_jp_panel(
    data_root: Path, as_of: str | None = None, fx_rate: float | None = None
) -> tuple[pd.DataFrame, PanelMetadata]:
    rows: list[pd.DataFrame] = []
    for source in discover_jp_daily_files(Path(data_root)):
        frame = pd.read_parquet(source)
        required = {"Date", "Code", "C", "Vo", "Va"}
        if not required.issubset(frame.columns):
            continue
        frame["date"] = pd.to_datetime(frame["Date"], errors="coerce").dt.date
        if as_of is not None:
            frame = frame.loc[frame["date"] <= pd.Timestamp(as_of).date()]
        if frame.empty:
            continue
        frame["symbol"] = frame["Code"].map(_normalize_code)
        frame["close"] = pd.to_numeric(frame["C"], errors="coerce")
        frame["volume"] = pd.to_numeric(frame["Vo"], errors="coerce")
        frame["turnover"] = pd.to_numeric(frame["Va"], errors="coerce")
        rows.append(
            pd.DataFrame(
                {
                    "market": "jp",
                    "symbol": frame["symbol"],
                    "date": frame["date"],
                    "close": frame["close"],
                    "volume": frame["volume"],
                    "turnover": frame["turnover"],
                    "market_cap": pd.NA,
                    "currency": "JPY",
                    "is_tradable": frame["close"].gt(0) & frame["volume"].gt(0),
                    "is_suspended": frame["close"].isna() | frame["volume"].isna(),
                    "source": str(source),
                }
            )
        )
    panel = pd.concat(rows, ignore_index=True) if rows else _empty_panel()
    end = str(panel["date"].max()) if not panel.empty else ""
    metadata = PanelMetadata(
        source="J-Quants/JPX daily bars via nira",
        as_of=as_of or end,
        currency="JPY",
        universe_filter="daily bars with positive close and volume marked tradable",
        fx_method="native JPY" if fx_rate is None else f"reference FX rate {fx_rate:g}",
        feature_lag=1,
        coverage_start=str(panel["date"].min()) if not panel.empty else None,
        coverage_end=str(panel["date"].max()) if not panel.empty else None,
        calendar_mode="observed_daily",
        quality_status="incomplete" if panel.empty or panel["market_cap"].isna().all() else "verified",
    )
    return normalize_panel(panel, metadata)


def _normalize_code(value: object) -> str:
    text = str(value)
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(5)


def _empty_panel() -> pd.DataFrame:
    return pd.DataFrame(columns=["market", "symbol", "date", "close", "volume", "turnover", "market_cap", "currency", "is_tradable", "is_suspended", "source"])
