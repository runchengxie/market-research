from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


DEFAULT_RANK_COUNTS = (1, 10, 50, 100, 200, 400, 1000)


def build_smallcap_turnover_stats(
    panel: pd.DataFrame,
    rank_counts: Iterable[int] = DEFAULT_RANK_COUNTS,
) -> pd.DataFrame:
    """Summarize daily turnover for the smallest A-share stocks by market cap.

    The panel is expected to contain the canonical research columns. Rows with
    non-positive market cap or turnover are excluded because the current
    cleaned A-share source defines them as non-eligible observations.
    """
    counts = tuple(rank_counts)
    if not counts or any(not isinstance(value, int) or value <= 0 for value in counts):
        raise ValueError("rank_counts must contain positive integers")

    required = {"market", "symbol", "date", "turnover", "market_cap"}
    missing = sorted(required.difference(panel.columns))
    if missing:
        raise ValueError("panel is missing columns: " + ",".join(missing))

    frame = panel.loc[panel["market"].eq("a_share")].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["turnover"] = pd.to_numeric(frame["turnover"], errors="coerce")
    frame["market_cap"] = pd.to_numeric(frame["market_cap"], errors="coerce")
    frame = frame.loc[
        frame["date"].notna()
        & frame["market_cap"].gt(0)
        & frame["turnover"].gt(0)
    ].copy()
    frame = frame.sort_values(["date", "market_cap", "symbol"], kind="stable")
    frame["cap_rank"] = frame.groupby("date", sort=False).cumcount() + 1

    rows: list[dict[str, object]] = []
    for date_value, daily in frame.groupby("date", sort=True):
        eligible_count = int(len(daily))
        for rank_count in counts:
            selected = daily.loc[daily["cap_rank"].le(rank_count)]
            turnover = selected["turnover"]
            market_cap = selected["market_cap"]
            rows.append(
                {
                    "date": date_value.date().isoformat(),
                    "rank_count": rank_count,
                    "eligible_count": eligible_count,
                    "selected_count": int(len(selected)),
                    "coverage_ratio": float(len(selected) / rank_count),
                    "turnover_sum": float(turnover.sum()),
                    "turnover_mean": float(turnover.mean()),
                    "turnover_median": float(turnover.median()),
                    "turnover_p10": float(turnover.quantile(0.10)),
                    "turnover_p25": float(turnover.quantile(0.25)),
                    "turnover_p75": float(turnover.quantile(0.75)),
                    "turnover_p90": float(turnover.quantile(0.90)),
                    "market_cap_median": float(market_cap.median()),
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "date", "rank_count", "eligible_count", "selected_count", "coverage_ratio",
            "turnover_sum", "turnover_mean", "turnover_median", "turnover_p10",
            "turnover_p25", "turnover_p75", "turnover_p90", "market_cap_median",
        ],
    )
