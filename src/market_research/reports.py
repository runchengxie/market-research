from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from .capacity import build_capacity_surface
from .contracts import PanelMetadata
from .liquidity import add_lagged_liquidity
from .quality import profile_panel


LIQUIDITY_PERIODS = {
    "2020-2024": ("2020-01-01", "2024-12-31"),
    "2025": ("2025-01-01", "2025-12-31"),
    "2026 YTD": ("2026-01-01", "2026-12-31"),
}


def build_liquidity_periods(
    panels: dict[str, pd.DataFrame],
    periods: dict[str, tuple[str, str]] | None = None,
) -> list[dict[str, object]]:
    """Build comparable period snapshots from each market's dated panel.

    Each market is bucketed independently on each observation date, then the
    bucket statistic is aggregated over the period. This avoids using the
    latest market-cap cross-section to explain historical liquidity.
    """
    period_specs = periods or LIQUIDITY_PERIODS
    result: list[dict[str, object]] = []
    for label, (start, end) in period_specs.items():
        period_markets: list[dict[str, object]] = []
        market_ranges: list[tuple[pd.Timestamp, pd.Timestamp]] = []
        for market, original in sorted(panels.items()):
            frame = original.copy()
            frame["date"] = pd.to_datetime(frame["date"])
            subset = frame.loc[frame["date"].between(start, end)].copy()
            if subset.empty:
                period_markets.append({"market": market, "status": "incomplete", "buckets": []})
                continue
            market_ranges.append((subset["date"].min(), subset["date"].max()))
            subset = add_lagged_liquidity(subset, windows=(20,))
            subset["cap_bucket"] = subset.groupby("date")["market_cap"].transform(
                lambda values: pd.cut(
                    values.rank(method="first", pct=True),
                    bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
                    labels=["<20%", "20-40%", "40-60%", "60-80%", ">=80%"],
                    include_lowest=True,
                )
            )
            valid = subset.loc[subset["adv20"].notna() & subset["cap_bucket"].notna()]
            buckets = []
            for bucket, values in valid.groupby("cap_bucket", observed=True):
                buckets.append({"label": str(bucket), "median_usd": float(values["adv20"].median()), "mean_usd": float(values["adv20"].mean()), "p90_usd": float(values["adv20"].quantile(0.9)), "observations": int(len(values))})
            period_markets.append({"market": market, "status": "verified" if buckets else "incomplete", "coverage_start": str(pd.Timestamp(subset["date"].min()).date()), "coverage_end": str(pd.Timestamp(subset["date"].max()).date()), "buckets": buckets})
        common_start = max(item[0] for item in market_ranges).date().isoformat() if market_ranges else None
        common_end = min(item[1] for item in market_ranges).date().isoformat() if market_ranges else None
        complete = len(period_markets) == len(panels) and all(item["status"] == "verified" for item in period_markets)
        result.append({"period": label, "status": "verified" if complete else "incomplete", "common_start": common_start, "common_end": common_end, "markets": period_markets})
    return result


def build_liquidity_report(
    panels: dict[str, pd.DataFrame], metadata: dict[str, PanelMetadata]
) -> dict[str, object]:
    summary: list[dict[str, object]] = []
    coverage: list[dict[str, object]] = []
    capacity_frames: list[pd.DataFrame] = []
    for market in sorted(panels):
        panel = add_lagged_liquidity(panels[market].copy(), windows=(20, 60))
        capacity_frames.append(panel)
        turnover = pd.to_numeric(panel["turnover"], errors="coerce")
        market_cap = pd.to_numeric(panel["market_cap"], errors="coerce")
        summary.append(
            {
                "market": market,
                "rows": int(len(panel)),
                "symbols": int(panel["symbol"].nunique(dropna=True)),
                "turnover_median": float(turnover.median()) if turnover.notna().any() else None,
                "turnover_mean": float(turnover.mean()) if turnover.notna().any() else None,
                "turnover_p90": float(turnover.quantile(0.9)) if turnover.notna().any() else None,
                "market_cap_missing_rows": int(market_cap.isna().sum()),
                "low_turnover_rows": int((turnover < turnover.quantile(0.1)).sum()) if turnover.notna().any() else 0,
            }
        )
        quality = profile_panel(panel)
        coverage.append({"market": market, **quality})
    return {
        "markets": sorted(panels),
        "summary": summary,
        "coverage": coverage,
        "metadata": {market: metadata[market].as_dict() for market in sorted(metadata)},
        "capacity_surface": build_capacity_surface(
            pd.concat(capacity_frames, ignore_index=True),
            participation_rates=(0.01, 0.05, 0.10),
            horizons=(1, 5, 10),
        ).to_dict(orient="records") if capacity_frames else [],
        "periods": build_liquidity_periods(panels),
    }


def write_report_bundle(report: dict[str, object], output_root: Path) -> None:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "liquidity_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    _write_rows(root / "liquidity_summary.csv", report.get("summary", []))
    _write_rows(root / "coverage_diagnostics.csv", report.get("coverage", []))
    _write_rows(root / "capacity_surface.csv", report.get("capacity_surface", []))


def _write_rows(path: Path, rows: object) -> None:
    values = list(rows) if isinstance(rows, list) else []
    fields = sorted({key for row in values if isinstance(row, dict) for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(values)
