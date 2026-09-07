from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from .capacity import build_capacity_surface
from .contracts import PanelMetadata
from .liquidity import add_lagged_liquidity
from .quality import profile_panel


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
