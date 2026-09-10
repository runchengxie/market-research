#!/usr/bin/env python3
"""Build an exploratory Japanese share-count sidecar from Yahoo Finance.

This output is suitable for local research validation only. It is not a
replacement for a licensed J-Quants Pro listed-shares dataset.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from market_research.markets.jp import build_jp_panel
from market_research.markets.yahoo import build_yfinance_shares_sidecar


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jp-root", type=Path, required=True, help="NIRA data root")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--code", action="append", help="Limit the trial to one or more JPX codes")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between Yahoo requests")
    parser.add_argument("--workers", type=int, default=1, help="Concurrent Yahoo requests")
    parser.add_argument("--parts-dir", type=Path, help="Checkpoint directory for resume")
    parser.add_argument("--error-log", type=Path, help="Append failed symbols here")
    args = parser.parse_args()

    panel, _ = build_jp_panel(args.jp_root, as_of=args.end, symbols=args.code)
    if args.start:
        panel = panel.loc[panel["date"] >= date.fromisoformat(args.start)]
    if args.code:
        codes = {str(code).zfill(5) for code in args.code}
        panel = panel.loc[panel["symbol"].isin(codes)]
    if panel.empty:
        raise SystemExit("No Japanese daily bars matched the requested range")

    parts_dir = args.parts_dir or args.output.with_suffix(".parts")
    result = build_yfinance_shares_sidecar(
        panel,
        args.output,
        start=args.start,
        end=args.end,
        parts_dir=parts_dir,
        delay_seconds=args.delay,
        error_path=args.error_log or args.output.with_suffix(".errors.tsv"),
        workers=args.workers,
    )
    symbols = result["symbol"].nunique() if not result.empty else 0
    print(f"wrote {len(result):,} rows for {symbols:,} symbols to {args.output}")


if __name__ == "__main__":
    main()
