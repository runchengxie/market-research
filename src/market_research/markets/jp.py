from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..contracts import PanelMetadata, normalize_panel


def discover_jp_daily_files(data_root: Path) -> list[Path]:
    return sorted(Path(data_root).rglob("equities_bars_daily_*.parquet"))


def build_jp_panel(
    data_root: Path,
    as_of: str | None = None,
    fx_rate: float | None = None,
    market_cap_path: Path | None = None,
) -> tuple[pd.DataFrame, PanelMetadata]:
    market_caps = _read_market_caps(market_cap_path) if market_cap_path else None
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
        frame["market_cap"] = pd.NA
        if market_caps is not None:
            frame = frame.merge(market_caps, on=["date", "symbol"], how="left", suffixes=("", "_sidecar"))
            frame["market_cap"] = pd.to_numeric(frame["market_cap_sidecar"], errors="coerce")
        if market_caps is not None and "shares_outstanding" in market_caps.columns:
            frame["market_cap"] = frame["market_cap"].fillna(frame["close"] * pd.to_numeric(frame["shares_outstanding"], errors="coerce"))
        rows.append(
            pd.DataFrame(
                {
                    "market": "jp",
                    "symbol": frame["symbol"],
                    "date": frame["date"],
                    "close": frame["close"],
                    "volume": frame["volume"],
                    "turnover": frame["turnover"],
                    "market_cap": frame["market_cap"],
                    "currency": "JPY",
                    "is_tradable": frame["close"].gt(0) & frame["volume"].gt(0),
                    "is_suspended": frame["close"].isna() | frame["volume"].isna(),
                    "source": str(source),
                }
            )
        )
    panel = pd.concat(rows, ignore_index=True) if rows else _empty_panel()
    if not panel.empty:
        panel = panel.drop_duplicates(["market", "symbol", "date"], keep="last")
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
        quality_status="verified" if not panel.empty and panel["market_cap"].notna().all() else "incomplete",
    )
    return normalize_panel(panel, metadata)


def _read_market_caps(path: Path) -> pd.DataFrame:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Japanese market-cap sidecar not found: {source}")
    frame = pd.read_parquet(source) if source.suffix.lower() == ".parquet" else pd.read_csv(source)
    date_column = next((column for column in ("Date", "date", "trade_date") if column in frame.columns), None)
    code_column = next((column for column in ("Code", "code", "symbol", "ticker") if column in frame.columns), None)
    cap_column = next((column for column in ("MarketCap", "market_cap", "market_cap_jpy") if column in frame.columns), None)
    shares_column = next((column for column in ("SharesOutstanding", "shares_outstanding", "shares") if column in frame.columns), None)
    if date_column is None or code_column is None or cap_column is None and shares_column is None:
        raise ValueError("Japanese market-cap sidecar requires date, code, and market cap or shares outstanding")
    result = pd.DataFrame({
        "date": pd.to_datetime(frame[date_column], errors="coerce").dt.date,
        "symbol": frame[code_column].map(_normalize_code),
    })
    if cap_column is not None:
        result["market_cap"] = pd.to_numeric(frame[cap_column], errors="coerce")
    if shares_column is not None:
        result["shares_outstanding"] = pd.to_numeric(frame[shares_column], errors="coerce")
    return result.dropna(subset=["date", "symbol"]).drop_duplicates(["date", "symbol"], keep="last")


def _normalize_code(value: object) -> str:
    text = str(value)
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(5)


def _empty_panel() -> pd.DataFrame:
    return pd.DataFrame(columns=["market", "symbol", "date", "close", "volume", "turnover", "market_cap", "currency", "is_tradable", "is_suspended", "source"])
