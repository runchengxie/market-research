from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path

import pandas as pd


WINDOWS = (3, 5, 10, 15, 20)


def _rows(nav: pd.DataFrame | Iterable[Mapping[str, object]]) -> list[tuple[str, float]]:
    frame = nav if isinstance(nav, pd.DataFrame) else pd.DataFrame(list(nav))
    if not {"date", "nav"}.issubset(frame.columns):
        raise ValueError("input must contain date and nav columns")
    rows = [(str(date), float(value)) for date, value in frame[["date", "nav"]].itertuples(index=False, name=None)]
    rows.sort()
    if not rows:
        raise ValueError("input contains no valid NAV records")
    return rows


def calculate_annual_returns(
    nav: pd.DataFrame | Iterable[Mapping[str, object]],
) -> pd.DataFrame:
    rows = _rows(nav)
    by_year: dict[int, list[float]] = {}
    for date, value in rows:
        by_year.setdefault(int(date[:4]), []).append(value)
    result: list[dict[str, float | int]] = []
    previous = None
    for year in sorted(by_year):
        value = by_year[year][-1]
        result.append({"year": year, "return": value / previous - 1 if previous is not None else value - 1, "nav": value})
        previous = value
    return pd.DataFrame(result, columns=["year", "return", "nav"])


def calculate_rolling_cagr(
    nav: pd.DataFrame | Iterable[Mapping[str, object]], windows: tuple[int, ...] = WINDOWS
) -> pd.DataFrame:
    annual = calculate_annual_returns(nav)
    result: list[dict[str, float | int | str]] = []
    for window in windows:
        if len(annual) < window + 1:
            continue
        for end in range(window, len(annual)):
            start_nav = float(annual.iloc[end - window]["nav"])
            end_nav = float(annual.iloc[end]["nav"])
            result.append({
                "as_of": f"{int(annual.iloc[end]['year'])}-12-31",
                "window_years": window,
                "cagr": (end_nav / start_nav) ** (1 / window) - 1,
            })
    return pd.DataFrame(result, columns=["as_of", "window_years", "cagr"])


def calculate_rolling_drawdown(
    nav: pd.DataFrame | Iterable[Mapping[str, object]],
    windows: tuple[int, ...] = WINDOWS,
    frequency: str = "annual_reference",
) -> pd.DataFrame:
    rows = _rows(nav)
    result: list[dict[str, float | int | str]] = []
    for window in windows:
        if len(rows) < window:
            continue
        for end in range(window - 1, len(rows)):
            sample = [value for _, value in rows[end - window + 1 : end + 1]]
            peak = sample[0]
            maximum = 0.0
            for value in sample:
                peak = max(peak, value)
                maximum = min(maximum, value / peak - 1)
            result.append({
                "as_of": rows[end][0],
                "window_years": window,
                "max_drawdown": maximum,
                "frequency": frequency,
            })
    return pd.DataFrame(result, columns=["as_of", "window_years", "max_drawdown", "frequency"])


def write_microcap_snapshot(nav: pd.DataFrame, output_root: Path, source_label: str) -> None:
    rows = _rows(nav)
    annual = calculate_annual_returns(nav)
    cagr = calculate_rolling_cagr(nav)
    drawdown = calculate_rolling_drawdown(nav)
    output_root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"date": [date for date, _ in rows], "nav": [value for _, value in rows], "source": source_label}).to_csv(output_root / "nav.csv", index=False)
    annual.to_csv(output_root / "annual_returns.csv", index=False)
    cagr.to_csv(output_root / "rolling_cagr.csv", index=False)
    drawdown.to_csv(output_root / "rolling_drawdown.csv", index=False)
    latest = annual.iloc[-1]
    latest_cagr = cagr.loc[cagr["as_of"].eq(f"{int(latest['year'])}-12-31")]
    summary = {
        "as_of": f"{int(latest['year'])}-12-31",
        "source_label": source_label,
        "coverage_start": str(int(annual.iloc[0]["year"])),
        "coverage_end": str(int(latest["year"])),
        "metrics": {"cumulative_nav": float(latest["nav"]), "annual_return": float(latest["return"])},
        "rolling_cagr": {str(int(row["window_years"])): float(row["cagr"]) for _, row in latest_cagr.iterrows()},
        "caveats": ["年度参考序列不等同于 Wind 原始日频序列。", "年度频率的回撤会低估日内和日间回撤。"],
    }
    (output_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
