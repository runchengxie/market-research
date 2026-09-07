from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..contracts import PanelMetadata, normalize_panel


def build_a_share_panel(
    data_root: Path,
    as_of: str | None = None,
    fx_rate: float | None = None,
    use_duckdb: bool = False,
) -> tuple[pd.DataFrame, PanelMetadata]:
    root = Path(data_root)
    if use_duckdb and root.is_dir():
        return _build_a_share_with_duckdb(root, as_of, fx_rate)
    rows: list[pd.DataFrame] = []
    sources = [root] if root.is_file() else sorted(root.rglob("*.parquet"))
    for source in sources:
        frame = pd.read_parquet(source)
        required = {"trade_date", "amount", "total_mv", "is_st", "is_suspended"}
        if not required.issubset(frame.columns):
            continue
        frame["date"] = pd.to_datetime(frame["trade_date"], errors="coerce").dt.date
        frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
        frame["total_mv"] = pd.to_numeric(frame["total_mv"], errors="coerce")
        frame["close"] = pd.to_numeric(frame.get("close"), errors="coerce")
        frame["adj_close"] = pd.to_numeric(frame.get("adj_close"), errors="coerce")
        frame["vol"] = pd.to_numeric(frame.get("vol"), errors="coerce")
        eligible = frame.loc[
            frame["date"].notna()
            & (frame["amount"] > 0)
            & (frame["total_mv"] > 0)
            & ~frame["is_st"].astype(bool)
            & ~frame["is_suspended"].astype(bool)
        ].copy()
        if as_of is not None:
            eligible = eligible.loc[eligible["date"] <= pd.Timestamp(as_of).date()]
        if eligible.empty:
            continue
        rows.append(
            pd.DataFrame(
                {
                    "market": "a_share",
                    "symbol": source.stem,
                    "date": eligible["date"],
                    "close": eligible["close"],
                    "adj_close": eligible["adj_close"],
                    "volume": eligible["vol"],
                    "turnover": eligible["amount"] * 1_000,
                    "market_cap": eligible["total_mv"] * 10_000,
                    "currency": "CNY",
                    "is_tradable": True,
                    "is_suspended": False,
                    "source": str(source),
                }
            )
        )
    panel = pd.concat(rows, ignore_index=True) if rows else _empty_panel()
    metadata = _metadata(panel, "Tushare A-share daily-clean", as_of, "CNY", fx_rate)
    return normalize_panel(panel, metadata)


def _build_a_share_with_duckdb(
    root: Path, as_of: str | None, fx_rate: float | None
) -> tuple[pd.DataFrame, PanelMetadata]:
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("DuckDB is required for use_duckdb=True") from exc
    pattern = str(root / "**" / "*.parquet")
    query = """
        SELECT ts_code, trade_date, close, adj_close, vol, amount, total_mv,
               is_st, is_suspended
        FROM read_parquet(?, union_by_name=true)
    """
    frame = duckdb.connect().execute(query, [pattern]).fetchdf()
    frame["date"] = pd.to_datetime(frame["trade_date"], errors="coerce").dt.date
    if as_of is not None:
        frame = frame.loc[frame["date"] <= pd.Timestamp(as_of).date()]
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    frame["total_mv"] = pd.to_numeric(frame["total_mv"], errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame["vol"] = pd.to_numeric(frame["vol"], errors="coerce")
    eligible = frame.loc[
        frame["date"].notna()
        & (frame["amount"] > 0)
        & (frame["total_mv"] > 0)
        & ~frame["is_st"].astype(bool)
        & ~frame["is_suspended"].astype(bool)
    ].copy()
    panel = pd.DataFrame(
        {
            "market": "a_share",
            "symbol": eligible["ts_code"].astype(str),
            "date": eligible["date"],
            "close": eligible["close"],
            "adj_close": eligible["adj_close"],
            "volume": eligible["vol"],
            "turnover": eligible["amount"] * 1_000,
            "market_cap": eligible["total_mv"] * 10_000,
            "currency": "CNY",
            "is_tradable": True,
            "is_suspended": False,
            "source": str(root),
        }
    )
    metadata = _metadata(panel, "Tushare A-share daily-clean DuckDB scan", as_of, "CNY", fx_rate)
    return normalize_panel(panel, metadata)


def _empty_panel() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "market", "symbol", "date", "close", "volume", "turnover", "market_cap",
            "currency", "is_tradable", "is_suspended", "source",
        ]
    )


def _metadata(panel: pd.DataFrame, source: str, as_of: str | None, currency: str, fx_rate: float | None) -> PanelMetadata:
    start = str(panel["date"].min()) if not panel.empty else None
    end = str(panel["date"].max()) if not panel.empty else None
    return PanelMetadata(
        source=source,
        as_of=as_of or end or "",
        currency=currency,
        universe_filter="positive amount/market cap; non-ST; non-suspended",
        fx_method="native currency" if fx_rate is None else f"reference FX rate {fx_rate:g}",
        feature_lag=1,
        coverage_start=start,
        coverage_end=end,
        calendar_mode="observed_daily",
        quality_status="verified" if not panel.empty else "incomplete",
    )
