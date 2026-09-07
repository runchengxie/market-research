from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

from .markets import build_a_share_panel, build_hk_panel, build_jp_panel, build_us_panel
from .indexes import build_nav, build_underwater_periods, reconstruct_smallest_cap_index, summarize_nav
from .reports import build_liquidity_report, write_report_bundle


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="market-research")
    subparsers = parser.add_subparsers(dest="command")
    config = subparsers.add_parser("config")
    config_subparsers = config.add_subparsers(dest="config_command")
    inspect = config_subparsers.add_parser("inspect")
    inspect.add_argument("--output-root", default="outputs")
    report = subparsers.add_parser("report")
    report_subparsers = report.add_subparsers(dest="report_command")
    liquidity = report_subparsers.add_parser("liquidity")
    liquidity.add_argument("--config", required=True)
    microcap = report_subparsers.add_parser("microcap")
    microcap.add_argument("--config", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--config", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            return 0
        raise
    if args.command == "config" and args.config_command == "inspect":
        print(json.dumps({"output_root": str(Path(args.output_root).expanduser().resolve())}))
        return 0
    if args.command == "validate":
        config = _load_config(Path(args.config))
        print(json.dumps({"configured_sources": sorted(_configured_source_names(config))}))
        return 0
    if args.command == "report" and args.report_command == "liquidity":
        config = _load_config(Path(args.config))
        panels, metadata = _build_configured_panels(config)
        if not panels:
            raise RuntimeError("no configured market source produced a panel")
        write_report_bundle(build_liquidity_report(panels, metadata), Path(config.get("output_root", "outputs")))
        return 0
    if args.command == "report" and args.report_command == "microcap":
        config = _load_config(Path(args.config))
        panels, _ = _build_configured_panels(config)
        if "a_share" not in panels:
            raise RuntimeError("A-share source is required for microcap report")
        output_root = Path(config.get("output_root", "outputs"))
        output_root.mkdir(parents=True, exist_ok=True)
        reconstruction = reconstruct_smallest_cap_index(panels["a_share"], constituent_count=400)
        nav = build_nav(reconstruction)
        nav.to_csv(output_root / "microcap_nav.csv", index=False)
        build_underwater_periods(nav).to_csv(output_root / "microcap_underwater_periods.csv", index=False)
        (output_root / "microcap_summary.json").write_text(
            json.dumps(
                {
                    "source_label": "market-research A-share rule reconstruction",
                    "method": "smallest 400 by market cap, equal weight, next market day return",
                    "observations": int(len(nav)),
                    **summarize_nav(nav),
                    "caveats": [
                        "Research reconstruction, not Wind 8841431.WI official index.",
                        "No transaction costs, limit handling, or strategy capacity simulation.",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return 0
    if args.command is None:
        parser.print_help()
    return 0


def _load_config(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    config.setdefault("sources", {})
    return config


def _configured_source_names(config: dict[str, object]) -> set[str]:
    sources = config.get("sources", {})
    if not isinstance(sources, dict):
        return set()
    return {name for name, value in sources.items() if value and Path(str(value)).exists()}


def _build_configured_panels(config: dict[str, object]):
    sources = config.get("sources", {})
    if not isinstance(sources, dict):
        return {}, {}
    as_of = config.get("as_of") or None
    panels = {}
    metadata = {}
    if sources.get("a_share_root") and Path(str(sources["a_share_root"])).exists():
        panels["a_share"], metadata["a_share"] = build_a_share_panel(Path(str(sources["a_share_root"])), as_of)
    if (
        sources.get("hk_daily_root")
        and sources.get("hk_valuation_root")
        and sources.get("hk_instruments_path")
        and Path(str(sources["hk_daily_root"])).exists()
        and Path(str(sources["hk_valuation_root"])).exists()
        and Path(str(sources["hk_instruments_path"])).exists()
    ):
        panels["hk"], metadata["hk"] = build_hk_panel(
            Path(str(sources["hk_daily_root"])),
            Path(str(sources["hk_valuation_root"])),
            Path(str(sources["hk_instruments_path"])),
            as_of,
        )
    if sources.get("us_shareprices_path") and Path(str(sources["us_shareprices_path"])).exists():
        panels["us"], metadata["us"] = build_us_panel(Path(str(sources["us_shareprices_path"])), as_of)
    if sources.get("jp_root") and Path(str(sources["jp_root"])).exists():
        panels["jp"], metadata["jp"] = build_jp_panel(Path(str(sources["jp_root"])), as_of)
    return panels, metadata
