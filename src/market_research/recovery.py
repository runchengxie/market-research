"""Historical recovery evidence, with unfinished observations kept censored.

Input must already have passed calendar and price-quality checks. A history
never establishes a finite upper bound on future recovery time.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


EPISODE_COLUMNS = ["peak_date", "trough_date", "recovery_date", "observed_until",
                   "calendar_days", "trading_sessions", "max_drawdown", "censored"]


def analyze_recovery(frame: pd.DataFrame, horizons=(1, 3, 5, 10)) -> dict:
    data = frame[["date", "nav"]].copy()
    data["date"] = pd.to_datetime(data.date, errors="raise")
    data["nav"] = pd.to_numeric(data.nav, errors="raise")
    if data.empty or data.date.isna().any() or data.date.duplicated().any():
        raise ValueError("recovery needs unique, nonempty dates")
    data = data.sort_values("date")
    values = data.nav.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("recovery needs finite positive prices; missing marks cannot be skipped")
    dates = pd.DatetimeIndex(data.date)
    n = len(values)

    def date(i):
        return dates[i].date().isoformat()

    def episode(peak, trough, end, censored):
        return {"peak_date": date(peak), "trough_date": date(trough),
                "recovery_date": None if censored else date(end), "observed_until": date(end),
                "calendar_days": int((dates[end] - dates[peak]).days),
                "trading_sessions": end - peak,
                "max_drawdown": float(values[trough] / values[peak] - 1), "censored": censored}

    peak, trough, active = 0, 0, False
    episodes = []
    for i in range(1, n):
        if values[i] >= values[peak]:
            if active:
                episodes.append(episode(peak, trough, i, False))
            peak, trough, active = i, i, False
        else:
            active = True
            if values[i] < values[trough]:
                trough = i
    if active:
        episodes.append(episode(peak, trough, n - 1, True))
    episodes_frame = pd.DataFrame(episodes, columns=EPISODE_COLUMNS)

    # Next observation at or above entry cost, including an equal-price touch.
    next_equal_or_higher = np.full(n, -1, dtype=int)
    stack = []
    for i, value in enumerate(values):
        while stack and value >= values[stack[-1]]:
            next_equal_or_higher[stack.pop()] = i
        stack.append(i)
    entries = []
    for i, j in enumerate(next_equal_or_higher):
        censored = j == -1
        end = n - 1 if censored else int(j)
        entries.append({"entry_date": date(i), "breakeven_date": None if censored else date(end),
                        "observed_until": date(end), "calendar_days": int((dates[end] - dates[i]).days),
                        "trading_sessions": end - i, "censored": censored,
                        "worst_return_before_breakeven": float(values[i:end + 1].min() / values[i] - 1)})

    horizon_rows = []
    for years in horizons:
        if not isinstance(years, int) or years <= 0:
            raise ValueError("horizons must be positive integer years")
        targets = dates + pd.DateOffset(years=years)
        exits = dates.searchsorted(targets)
        mature = exits < n
        returns = values[exits[mature]] / values[mature] - 1
        horizon_rows.append({"years": years, "mature_entries": int(mature.sum()),
                             "immature_entries": int((~mature).sum()),
                             "loss_fraction": float((returns < 0).mean()) if len(returns) else None,
                             "worst_return": float(returns.min()) if len(returns) else None,
                             "median_return": float(np.median(returns)) if len(returns) else None})
    complete = [row for row in episodes if not row["censored"]]
    summary = {
        "start": date(0), "end": date(n - 1), "observations": n,
        "completed_episode_count": len(complete),
        "longest_completed_underwater_calendar_days": max((r["calendar_days"] for r in complete), default=None),
        "longest_observed_underwater_calendar_days": max((r["calendar_days"] for r in episodes), default=0),
        "currently_underwater": active,
        "current_underwater_calendar_days": int((dates[-1] - dates[peak]).days) if active else 0,
        "current_peak_date": date(peak) if active else None,
        "gain_needed_to_recover": float(values[peak] / values[-1] - 1) if active else 0.0,
        "unrecovered_entry_count": sum(r["censored"] for r in entries),
        "historical_only": True,
    }
    return {"summary": summary, "episodes": episodes_frame,
            "entries": pd.DataFrame(entries), "horizons": pd.DataFrame(horizon_rows)}
