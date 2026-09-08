from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

from .loader import LOCAL_CURRENCY, MARKETS


def build_month_end_calendar(assets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for market, frame in assets.items():
        dates = pd.DatetimeIndex(sorted(frame["date"]))
        for _, month in frame.groupby(frame["date"].dt.to_period("M")):
            observation = month["date"].max()
            following = dates[dates > observation]
            rows.append({"market": market, "observation_date": observation, "next_session": following[0] if len(following) else pd.NaT})
    return pd.DataFrame(rows).sort_values(["observation_date", "market"]).reset_index(drop=True)


def _aligned_return(frame: pd.DataFrame, dates: pd.DatetimeIndex, market: str) -> pd.Series:
    prices = frame.set_index("date")["close"].sort_index()
    aligned = prices.reindex(dates).ffill()
    if aligned.isna().any():
        raise ValueError(f"asset series has no prior close for {market}")
    gaps = prices.index.to_series().diff().dt.days.dropna()
    if not gaps.empty and gaps.max() > 7 and gaps.median() <= 7:
        raise ValueError(f"asset series has stale/missing observations for {market}")
    return aligned.pct_change().fillna(0.0)


def compute_usd_return_components(assets: dict[str, pd.DataFrame], fx: dict[str, pd.DataFrame], distributions: dict[str, pd.DataFrame], target_weights: Mapping[str, float], cost_bps: Mapping[str, float]) -> pd.DataFrame:
    if set(assets) != set(MARKETS) or abs(sum(target_weights.values()) - 1.0) > 1e-9:
        raise ValueError("assets and target weights must contain the six markets and sum to one")
    common_start = max(frame["date"].min() for frame in [*assets.values(), *fx.values()])
    dates = pd.DatetimeIndex(sorted({date for frame in assets.values() for date in frame["date"] if date >= common_start}))
    daily = pd.DataFrame(index=dates)
    for market in MARKETS:
        local = _aligned_return(assets[market], dates, market)
        currency = LOCAL_CURRENCY[market]
        if currency == "USD":
            fx_return = pd.Series(0.0, index=dates)
        else:
            rates = fx[currency].set_index("date")["usd_per_local"].reindex(dates).ffill()
            if rates.isna().any():
                raise ValueError(f"FX series has no prior rate for {currency}")
            fx_return = rates.pct_change().fillna(0.0)
        dividend = pd.Series(0.0, index=dates)
        cash = distributions.get(market, pd.DataFrame())
        prices = assets[market].set_index("date")["close"].sort_index()
        for row in cash.itertuples(index=False):
            effective = prices.index[prices.index >= row.date]
            prior = prices.loc[prices.index < effective[0]] if len(effective) else pd.Series(dtype=float)
            if prior.empty:
                raise ValueError(f"distribution has no prior close for {market}")
            dividend.loc[effective[0]] += row.cash_per_share / prior.iloc[-1]
        daily[market] = (1 + local) * (1 + fx_return) * (1 + dividend) - 1
    calendar = build_month_end_calendar(assets)
    rebalances = {date: group for date, group in calendar.groupby(calendar["next_session"].fillna(calendar["observation_date"]))}
    holdings = pd.Series({market: float(target_weights[market]) for market in MARKETS})
    rows = []
    for date, returns in daily.iterrows():
        total = float(holdings.sum())
        weights = holdings / total
        gross = float(sum(weights[m] * returns[m] for m in MARKETS))
        holdings *= 1 + returns
        turnover = 0.0
        cost = 0.0
        events = rebalances.get(date, pd.DataFrame())
        for event in events.itertuples(index=False):
            target = total * float(target_weights[event.market])
            trade = target - float(holdings[event.market])
            turnover += abs(trade) / total
            cost += abs(trade) / total * float(cost_bps[event.market]) / 10_000
            holdings[event.market] = target
        holdings *= 1 - cost
        rows.append({"date": date, "gross_return": gross, "portfolio_return": gross - cost, "turnover": turnover, "cost_drag": cost, "rebalance_markets": ",".join(events["market"].tolist()) if not events.empty else ""})
    result = pd.DataFrame(rows)
    result.attrs["total_return_status"] = "complete" if all(not distributions.get(m, pd.DataFrame()).empty for m in MARKETS) else "unavailable"
    return result


def summarize_portfolio(returns: pd.DataFrame) -> dict[str, float]:
    daily = pd.to_numeric(returns["portfolio_return"], errors="raise").fillna(0.0)
    nav = (1 + daily).cumprod()
    vol = float(daily.std(ddof=1) * np.sqrt(252)) if len(daily) > 1 else 0.0
    return {"annualized_return": float(nav.iloc[-1] ** (252 / len(daily)) - 1) if len(daily) else 0.0, "annualized_volatility": vol, "annualized_sharpe": float((nav.iloc[-1] ** (252 / len(daily)) - 1) / vol) if len(daily) and vol else 0.0, "maximum_drawdown": float((nav / nav.cummax() - 1).min()) if len(daily) else 0.0, "turnover": float(returns["turnover"].sum()) if len(daily) else 0.0}
