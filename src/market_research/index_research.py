from __future__ import annotations

import re
import os
import time
from pathlib import Path

import pandas as pd


TOTAL_RETURN_CODES = {
    "932365.CSI": "932365CNY010.CSI",
    "932366.CSI": "932366CNY010.CSI",
    "932367.CSI": "932367CNY010.CSI",
    "932368.CSI": "932368CNY010.CSI",
    "932369.CSI": "932369CNY010.CSI",
    "931082.CSI": "931082CNY010.CSI",
    "932457.CSI": "932457HKD210.CSI",
}

DEFAULT_CASHFLOW_INDEXES = (
    ("980092.SZ", "国证自由现金流", "Broad A-share / red-chip", "quarterly", "current rule; changed 2024-08-15"),
    ("932365.CSI", "中证全指自由现金流", "CSI All Share", "quarterly", "100 constituents"),
    ("932366.CSI", "300现金流", "CSI 300", "quarterly", "50 constituents"),
    ("932367.CSI", "500现金流", "CSI 500", "quarterly", "50 constituents"),
    ("932368.CSI", "800现金流", "CSI 800", "quarterly", "50 constituents"),
    ("932369.CSI", "1000现金流", "CSI 1000", "quarterly", "100 constituents"),
    ("931082.CSI", "A500现金流", "CSI A500", "quarterly", "50 constituents"),
    ("932457.CSI", "港股通现金流", "Hong Kong Connect", "semiannual", "50 constituents; HKD"),
)


def api_for_index_code(ts_code: str) -> str | None:
    upper = str(ts_code).upper()
    suffix = upper.rsplit(".", 1)[-1] if "." in upper else ""
    return {
        "SH": "index_daily", "SZ": "index_daily", "BJ": "index_daily", "CSI": "index_daily",
        "CNI": "index_daily", "SI": "sw_daily", "CI": "ci_daily", "TI": "ths_daily",
    }.get(suffix)


def _tushare_client():
    token = os.getenv("TUSHARE_TOKEN_2") or os.getenv("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError("TUSHARE_TOKEN_2 or TUSHARE_TOKEN is not configured")
    import tushare as ts

    client = ts.pro_api(token=token)
    api_url = os.getenv("TUSHARE_API_URL_2") or os.getenv("TUSHARE_API_URL")
    if api_url:
        client._DataApi__http_url = api_url
    return client


def fetch_linked_indices(
    mapping_csv: Path, out_dir: Path, start_date: str = "20150101", end_date: str = "20260821",
    sleep_seconds: float = 0.15, client=None,
) -> None:
    mapping = pd.read_csv(mapping_csv, dtype={"ts_code": str}).drop_duplicates("ts_code").copy()
    mapping["api"] = mapping["ts_code"].map(api_for_index_code)
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(out_dir / "linked_index_catalog.csv", index=False)
    client = client or _tushare_client()
    frames: list[pd.DataFrame] = []
    status: list[dict[str, object]] = []
    for row in mapping.itertuples(index=False):
        code, api = str(row.ts_code), row.api
        if not api or pd.isna(api):
            status.append({"ts_code": code, "api": None, "status": "unsupported_code_suffix", "rows": 0})
            continue
        try:
            frame = getattr(client, api)(ts_code=code, start_date=start_date, end_date=end_date)
            if frame.empty:
                status.append({"ts_code": code, "api": api, "status": "empty", "rows": 0})
            else:
                frame = frame.copy()
                frame["api"] = api
                frames.append(frame)
                status.append({"ts_code": code, "api": api, "status": "ok", "rows": len(frame)})
        except Exception as exc:
            status.append({"ts_code": code, "api": api, "status": "error", "rows": 0, "error": str(exc)[:300]})
        if sleep_seconds:
            time.sleep(sleep_seconds)
    pd.DataFrame(status).to_csv(out_dir / "linked_index_fetch_status.csv", index=False)
    if frames:
        pd.concat(frames, ignore_index=True).to_parquet(out_dir / "linked_index_daily.parquet", index=False)


def refresh_cashflow_indices(
    out_dir: Path, start_date: str = "20100101", end_date: str = "20260904", client=None, indexes=DEFAULT_CASHFLOW_INDEXES
) -> None:
    client = client or _tushare_client()
    codes = [str(row[0]) for row in indexes]
    if indexes is DEFAULT_CASHFLOW_INDEXES:
        codes.extend(TOTAL_RETURN_CODES.values())
    frames = []
    for code in codes:
        frame = client.index_daily(ts_code=code, start_date=start_date, end_date=end_date)
        if not frame.empty:
            frame = frame.copy()
            frame["api"] = "index_daily"
            frames.append(frame)
    if not frames:
        raise RuntimeError("TuShare returned no cash-flow index data")
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.concat(frames, ignore_index=True).to_parquet(out_dir / "cashflow_index_daily.parquet", index=False)


def build_index_price_snapshot(index_daily: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    frame = index_daily.copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"].astype(str), format="%Y%m%d", errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    rows = []
    for code, group in frame.dropna(subset=["trade_date", "close"]).groupby("ts_code", sort=True):
        endpoints = group.set_index(group["trade_date"].dt.strftime("%Y%m%d"))["close"]
        if start_date not in endpoints or end_date not in endpoints:
            continue
        p0, p1 = float(endpoints[start_date]), float(endpoints[end_date])
        rows.append({"ts_code": code, "p0": p0, "p1": p1, "price_return": p1 / p0 - 1, "cagr": (p1 / p0) ** 0.1 - 1})
    return pd.DataFrame(rows, columns=["ts_code", "p0", "p1", "price_return", "cagr"]).sort_values("cagr", ascending=False).reset_index(drop=True)


def match_index_name(benchmark: str, index_names: list[str]) -> str | None:
    text = re.sub(r"\s+", "", str(benchmark))
    candidates = [name for name in index_names if name and name in text]
    return max(candidates, key=len) if candidates else None


def build_etf_index_pairing(etf_basic: pd.DataFrame, index_catalog: pd.DataFrame, start_date: int = 20160902) -> pd.DataFrame:
    frame = etf_basic.copy()
    frame["list_date"] = pd.to_numeric(frame["list_date"], errors="coerce")
    eligible = frame[
        frame["status"].eq("L") & frame["fund_type"].eq("股票型") & frame["name"].fillna("").str.contains("ETF", regex=False)
        & frame["list_date"].notna() & frame["list_date"].le(start_date) & frame["benchmark"].notna()
    ].copy()
    names = index_catalog["indx_name"].dropna().astype(str).unique().tolist()
    eligible["matched_index_name"] = eligible["benchmark"].map(lambda value: match_index_name(value, names))
    mapping = index_catalog.drop_duplicates("indx_name").set_index("indx_name")["ts_code"].to_dict()
    eligible["index_ts_code"] = eligible["matched_index_name"].map(mapping)
    return eligible[eligible["index_ts_code"].notna()].reset_index(drop=True)


def build_etf_index_metrics(
    etf_daily: pd.DataFrame, index_daily: pd.DataFrame, etf_code: str, index_code: str, start_date: str, end_date: str
) -> dict[str, float | str | None]:
    etf = etf_daily.loc[etf_daily["ts_code"].eq(etf_code)].copy()
    index = index_daily.loc[index_daily["ts_code"].eq(index_code)].copy()
    for frame in (etf, index):
        frame["trade_date"] = pd.to_datetime(frame["trade_date"].astype(str), format="%Y%m%d", errors="coerce")
    etf = etf.set_index("trade_date").sort_index()
    index = index.set_index("trade_date").sort_index()
    start, end = pd.Timestamp(start_date), pd.Timestamp(end_date)
    etf_window = etf.loc[start:end]
    index_window = index.loc[start:end]
    if etf_window.empty or index_window.empty:
        raise ValueError("ETF and index windows must contain observations")
    etf_values = pd.to_numeric(etf_window["adj_close"], errors="coerce").dropna()
    index_values = pd.to_numeric(index_window["close"], errors="coerce").dropna()
    if etf_values.empty or index_values.empty:
        raise ValueError("ETF and index windows must contain valid prices")
    etf_peak = etf_values.cummax()
    index_peak = index_values.cummax()
    return {
        "ts_code": etf_code,
        "index_ts_code": index_code,
        "etf_total_return": float(etf_values.iloc[-1] / etf_values.iloc[0] - 1),
        "etf_max_drawdown": float((etf_values / etf_peak - 1).min()),
        "index_price_return": float(index_values.iloc[-1] / index_values.iloc[0] - 1),
        "index_max_drawdown": float((index_values / index_peak - 1).min()),
    }


def build_cashflow_snapshot(raw: pd.DataFrame, indexes=DEFAULT_CASHFLOW_INDEXES) -> dict[str, pd.DataFrame]:
    frame = raw.copy()
    frame["date"] = pd.to_datetime(frame["trade_date"].astype(str), format="%Y%m%d", errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["date", "close"]).sort_values(["ts_code", "date"])
    available_end = frame["date"].max()
    performance: list[dict[str, object]] = []
    status: list[dict[str, object]] = []
    for code, name, universe, frequency, note in indexes:
        total_code = TOTAL_RETURN_CODES.get(code)
        total = frame[frame["ts_code"].eq(total_code)] if total_code else frame.iloc[0:0]
        selected = total if not total.empty else frame[frame["ts_code"].eq(code)]
        basis = "gross_total_return" if not total.empty else "price_return"
        source_code = total_code if basis == "gross_total_return" else code
        status.append({"ts_code": code, "name": name, "source_code": source_code, "return_basis": basis, "status": "available" if not selected.empty else "missing", "coverage_start": selected["date"].min().date().isoformat() if not selected.empty else None, "coverage_end": selected["date"].max().date().isoformat() if not selected.empty else None, "rows": int(len(selected))})
        if selected.empty:
            continue
        series = selected.set_index("date")["close"]
        start_date, start_close = series.index[0], float(series.iloc[0])
        end_date, end_close = series.index[-1], float(series.iloc[-1])
        ret = end_close / start_close - 1
        years = max((end_date - start_date).days / 365.25, 1 / 365.25)
        performance.append({"ts_code": code, "name": name, "universe": universe, "rebalance_frequency": frequency, "return_basis": basis, "source_code": source_code, "note": note, "window": "full_available", "status": "ok", "as_of": available_end.date().isoformat(), "start_date": start_date.date().isoformat(), "end_date": end_date.date().isoformat(), "start_close": start_close, "end_close": end_close, "return": ret, "cagr": (1 + ret) ** (1 / years) - 1})
    return {"performance": pd.DataFrame(performance), "status": pd.DataFrame(status), "rebalance_frequency": pd.DataFrame(indexes, columns=["ts_code", "name", "universe", "rebalance_frequency", "note"])}
