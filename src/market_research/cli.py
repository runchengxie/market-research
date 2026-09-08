from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

import pandas as pd

from .barra import analyze_size_monotonicity, load_barra_summary
from .markets import build_a_share_panel, build_hk_panel, build_jp_panel, build_us_panel
from .indexes import (
    build_nav,
    build_underwater_periods,
    reconstruct_smallest_cap_index,
    reconstruct_smallest_cap_index_from_parquet,
    summarize_nav,
)
from .reports import build_liquidity_report, write_report_bundle
from .microcap import write_microcap_snapshot
from .index_research import (
    build_cashflow_snapshot,
    build_etf_proxy_returns,
    build_etf_pair_report,
    build_index_price_snapshot,
    fetch_linked_indices,
    refresh_cashflow_indices,
)


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
    indices = report_subparsers.add_parser("indices")
    indices.add_argument("--config", required=True)
    cashflow = report_subparsers.add_parser("cashflow")
    cashflow.add_argument("--config", required=True)
    etf_pairs = report_subparsers.add_parser("etf-pairs")
    etf_pairs.add_argument("--config", required=True)
    barra = report_subparsers.add_parser("barra")
    barra.add_argument("--config", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--config", required=True)
    fetch = subparsers.add_parser("fetch")
    fetch_subparsers = fetch.add_subparsers(dest="fetch_command")
    linked = fetch_subparsers.add_parser("linked-indices")
    linked.add_argument("--config", required=True)
    cashflow_fetch = fetch_subparsers.add_parser("cashflow")
    cashflow_fetch.add_argument("--config", required=True)
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
    if args.command == "fetch":
        config = _load_config(Path(args.config))
        if args.fetch_command == "linked-indices":
            mapping = _index_research_path(config, "mapping_csv")
            if mapping is None:
                raise RuntimeError("index_research.mapping_csv is required")
            output = Path(config.get("output_root", "outputs")) / "linked_indices"
            fetch_linked_indices(mapping, output, start_date=str(config.get("index_start_date", "20150101")), end_date=str(config.get("index_end_date", "20260821")))
            return 0
        if args.fetch_command == "cashflow":
            output = Path(config.get("output_root", "outputs")) / "cashflow_indices"
            refresh_cashflow_indices(output, end_date=str(config.get("index_end_date", "20260904")))
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
        sources = config.get("sources", {})
        a_share_root = Path(str(sources.get("a_share_root", ""))) if isinstance(sources, dict) else Path("")
        if not a_share_root.exists():
            raise RuntimeError("A-share source is required for microcap report")
        output_root = Path(config.get("output_root", "outputs"))
        output_root.mkdir(parents=True, exist_ok=True)
        if bool(config.get("use_duckdb", False)) and a_share_root.is_dir():
            reconstruction = reconstruct_smallest_cap_index_from_parquet(a_share_root, constituent_count=400)
        else:
            panels, _ = _build_configured_panels(config)
            if "a_share" not in panels:
                raise RuntimeError("A-share source did not produce a valid panel")
            reconstruction = reconstruct_smallest_cap_index(panels["a_share"], constituent_count=400)
        nav = build_nav(reconstruction)
        nav.to_csv(output_root / "microcap_nav.csv", index=False)
        build_underwater_periods(nav).to_csv(output_root / "microcap_underwater_periods.csv", index=False)
        write_microcap_snapshot(nav[["date", "nav"]], output_root / "microcap", "market-research A-share rule reconstruction")
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
    if args.command == "report" and args.report_command == "barra":
        config = _load_config(Path(args.config))
        sources = config.get("sources", {})
        barra_config = config.get("barra", {})
        if not isinstance(sources, dict) or not sources.get("a_share_root"):
            raise RuntimeError("A-share source is required for Barra report")
        a_share_root = Path(str(sources["a_share_root"]))
        if not a_share_root.exists():
            raise RuntimeError("configured A-share source does not exist")
        if not isinstance(barra_config, dict):
            barra_config = {}
        output_root = Path(config.get("output_root", "outputs"))
        output_root.mkdir(parents=True, exist_ok=True)
        panel, panel_metadata = build_a_share_panel(
            a_share_root,
            config.get("as_of") or None,
            use_duckdb=bool(config.get("use_duckdb", False)),
        )
        quantile_rows, size_summary = analyze_size_monotonicity(
            panel,
            int(barra_config.get("size_quantiles", 10)),
            int(barra_config.get("holding_period", 1)),
        )
        result_root = barra_config.get("result_root")
        history_summary = load_barra_summary(Path(str(result_root))) if result_root else None
        (output_root / "barra_summary.json").write_text(
            json.dumps(
                {
                    "analysis": "size factor cross-sectional forward-return monotonicity",
                    "source": panel_metadata.as_dict(),
                    "size_monotonicity": size_summary,
                    "legacy_barra_result": history_summary,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )
        quantile_rows.to_csv(output_root / "barra_size_quantiles.csv", index=False)
        (output_root / "barra_source_manifest.json").write_text(
            json.dumps(
                {
                    "canonical_project": "market-research",
                    "historical_source": str(result_root) if result_root else None,
                    "panel_source": str(a_share_root),
                    "raw_data_copied": False,
                    "factor_count_in_historical_source": history_summary.get("factor_count") if history_summary else None,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return 0
    if args.command == "report" and args.report_command == "indices":
        config = _load_config(Path(args.config))
        source = _index_research_path(config, "index_daily_path")
        if source is None:
            raise RuntimeError("index_research.index_daily_path is required")
        frame = _read_table(source)
        start = str(config.get("index_start_date", "20160902"))
        end = str(config.get("index_end_date", config.get("as_of", "20260821"))).replace("-", "")
        result = build_index_price_snapshot(frame, start, end)
        output = Path(config.get("output_root", "outputs"))
        output.mkdir(parents=True, exist_ok=True)
        result.to_csv(output / "a_share_index_price_returns.csv", index=False)
        etf_daily = _index_research_path(config, "etf_daily_path")
        factors = _index_research_path(config, "etf_adj_factor_path")
        basic = _index_research_path(config, "etf_basic_path")
        if etf_daily and factors and basic:
            build_etf_proxy_returns(_read_table(etf_daily), _read_table(factors), _read_table(basic), start, end).to_csv(output / "etf_proxy_returns.csv", index=False)
        return 0
    if args.command == "report" and args.report_command == "cashflow":
        config = _load_config(Path(args.config))
        source = _index_research_path(config, "linked_index_daily_path")
        if source is None:
            raise RuntimeError("index_research.linked_index_daily_path is required")
        outputs = build_cashflow_snapshot(_read_table(source))
        output = Path(config.get("output_root", "outputs")) / "cashflow_indices"
        output.mkdir(parents=True, exist_ok=True)
        outputs["performance"].to_csv(output / "cashflow_performance.csv", index=False)
        outputs["status"].to_csv(output / "cashflow_data_status.csv", index=False)
        outputs["rebalance_frequency"].to_csv(output / "cashflow_rebalance_frequency.csv", index=False)
        return 0
    if args.command == "report" and args.report_command == "etf-pairs":
        config = _load_config(Path(args.config))
        required = {key: _index_research_path(config, key) for key in ("index_catalog_path", "etf_basic_path", "etf_daily_path", "etf_adj_factor_path", "index_daily_path")}
        if any(path is None for path in required.values()):
            raise RuntimeError("index_research index catalog, ETF basic/daily/adjustment, and index daily paths are required")
        section = config.get("index_research", {})
        start = str(section.get("index_start_date", "20160902")) if isinstance(section, dict) else "20160902"
        end = str(section.get("index_end_date", "20260821")) if isinstance(section, dict) else "20260821"
        reports = build_etf_pair_report(
            _read_table(required["etf_basic_path"]), _read_table(required["index_catalog_path"]),
            _read_table(required["etf_daily_path"]), _read_table(required["etf_adj_factor_path"]),
            _read_table(required["index_daily_path"]), start, end,
        )
        output = Path(config.get("output_root", "outputs")) / "linked_indices"
        output.mkdir(parents=True, exist_ok=True)
        reports["pairing"].to_csv(output / "etf_index_pairing.csv", index=False)
        reports["all"].to_csv(output / "paired_index_etf_returns_all.csv", index=False)
        reports["representatives"].to_csv(output / "paired_index_etf_representatives.csv", index=False)
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


def _index_research_path(config: dict[str, object], key: str) -> Path | None:
    section = config.get("index_research", {})
    if not isinstance(section, dict) or not section.get(key):
        return None
    path = Path(str(section[key])).expanduser()
    return path if path.exists() else None


def _read_table(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)


def _build_configured_panels(config: dict[str, object]):
    sources = config.get("sources", {})
    if not isinstance(sources, dict):
        return {}, {}
    as_of = config.get("as_of") or None
    panels = {}
    metadata = {}
    if sources.get("a_share_root") and Path(str(sources["a_share_root"])).exists():
        panels["a_share"], metadata["a_share"] = build_a_share_panel(
            Path(str(sources["a_share_root"])),
            as_of,
            use_duckdb=bool(config.get("use_duckdb", False)),
        )
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
