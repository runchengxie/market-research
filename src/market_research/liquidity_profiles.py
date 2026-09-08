from __future__ import annotations

import pandas as pd


BUCKETS = ("<1千万", "1千万-1亿", "1亿-10亿", "10亿-100亿", ">=100亿")


def _snapshot(panel: pd.DataFrame) -> pd.DataFrame:
    frame = panel.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.sort_values("date", kind="stable").groupby(["market", "symbol"], as_index=False, sort=False).tail(1).copy()


def _bucket(value: float) -> str:
    if value < 1e7:
        return "<1千万"
    if value < 1e8:
        return "1千万-1亿"
    if value < 1e9:
        return "1亿-10亿"
    if value < 1e10:
        return "10亿-100亿"
    return ">=100亿"


def _prepared(panel: pd.DataFrame, fx_rate: float) -> pd.DataFrame:
    frame = _snapshot(panel)
    frame["market_cap_usd"] = pd.to_numeric(frame["market_cap"], errors="coerce") * fx_rate
    source = "medadv20" if "medadv20" in frame.columns else "turnover"
    frame["avg_turnover_native"] = pd.to_numeric(frame[source], errors="coerce")
    frame["avg_turnover_usd"] = frame["avg_turnover_native"] * fx_rate
    frame = frame.loc[frame["market_cap_usd"].gt(0) & frame["avg_turnover_usd"].gt(0)].copy()
    frame["bucket"] = frame["market_cap_usd"].map(_bucket)
    return frame


def build_bucket_summary(panel: pd.DataFrame, currency: str = "USD", fx_rate: float = 1.0) -> pd.DataFrame:
    frame = _prepared(panel, fx_rate)
    rows = []
    for bucket in BUCKETS:
        group = frame.loc[frame["bucket"].eq(bucket), "avg_turnover_usd"]
        rows.append({
            "bucket": bucket,
            "count": int(len(group)),
            "median_usd": float(group.median()) if not group.empty else None,
            "mean_usd": float(group.mean()) if not group.empty else None,
            "p90_usd": float(group.quantile(0.9)) if not group.empty else None,
            "currency": currency,
        })
    return pd.DataFrame(rows)


def build_cross_market_summary(panels: dict[str, pd.DataFrame], fx_rates: dict[str, float]) -> pd.DataFrame:
    rows = []
    for market in sorted(panels):
        summary = build_bucket_summary(panels[market], currency="USD", fx_rate=float(fx_rates.get(market, 1.0)))
        summary.insert(0, "market", market)
        rows.append(summary)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["market", "bucket", "count", "median_usd", "mean_usd", "p90_usd", "currency"])


def build_instrument_diagnostics(panel: pd.DataFrame, fx_rate: float = 1.0) -> pd.DataFrame:
    frame = _prepared(panel, fx_rate)
    result = frame.loc[frame["market_cap_usd"].lt(1e8), ["market", "symbol", "market_cap_usd", "avg_turnover_usd", "bucket"]].copy()
    return result.sort_values(["avg_turnover_usd", "symbol"], kind="stable").reset_index(drop=True)


def build_cross_sectional_ranking(panel: pd.DataFrame, target_symbol: str) -> pd.DataFrame:
    """Rank a target instrument against its same-market daily universe."""
    frame = panel.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["turnover"] = pd.to_numeric(frame["turnover"], errors="coerce")
    frame["volume"] = pd.to_numeric(frame.get("volume"), errors="coerce")
    frame = frame.loc[
        frame["turnover"].gt(0)
        & ~frame.get("is_st", False).astype(bool)
        & ~frame.get("is_suspended", False).astype(bool)
    ].copy()
    frame["amount_rank"] = frame.groupby(["market", "date"])["turnover"].rank(method="first")
    frame["volume_rank"] = frame.groupby(["market", "date"])["volume"].rank(method="first")
    frame["day_count"] = frame.groupby(["market", "date"])["symbol"].transform("count")
    frame["amount_percentile"] = frame["amount_rank"] / frame["day_count"] * 100
    frame["volume_percentile"] = frame["volume_rank"] / frame["day_count"] * 100
    return frame.loc[frame["symbol"].eq(target_symbol)].sort_values(["market", "date"], kind="stable").reset_index(drop=True)
