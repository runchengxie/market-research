from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .barra import analyze_size_monotonicity, load_barra_summary
from .style_portfolios import build_quantile_returns, summarize_market_factor_evidence
from .studies.global_six_market.run import run_experiment as run_global_six_market
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
from .smallcap_turnover import DEFAULT_RANK_COUNTS, build_smallcap_turnover_stats
from .smallcap_turnover_history import load_historical_turnover_panel
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
    smallcap_turnover = report_subparsers.add_parser("smallcap-turnover")
    smallcap_turnover.add_argument("--config", required=True)
    smallcap_turnover_history = report_subparsers.add_parser("smallcap-turnover-history")
    smallcap_turnover_history.add_argument("--config", required=True)
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
    style = report_subparsers.add_parser("style-factors")
    style.add_argument("--study", required=True)
    global_six = report_subparsers.add_parser("global-six-market")
    global_six.add_argument("--study", required=True)
    index_study = report_subparsers.add_parser("index-study")
    index_study.add_argument("--study", required=True)
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
    if args.command == "report" and args.report_command == "index-study":
        from .studies.index_study import run_study
        print(run_study(Path(args.study)))
        return 0
    if args.command == "report" and args.report_command == "style-factors":
        study = _load_yaml(Path(args.study))
        panel_path = Path(str(study.get("panel_path", "")))
        if not panel_path.is_file():
            raise RuntimeError("style study panel_path must point to an external CSV")
        panel = pd.read_csv(panel_path)
        factor = str(study.get("factor_column", "factor"))
        rows = build_quantile_returns(panel, factor, int(study.get("quantiles", 10)), int(study.get("holding_period", 1)))
        summary = summarize_market_factor_evidence(rows, factor, {"study_id": study.get("study_id"), "window_years": study.get("window_years")})
        output = Path(str(study.get("output_root", "outputs")))
        output.mkdir(parents=True, exist_ok=True)
        rows.to_csv(output / "style_factor_quantiles.csv", index=False)
        (output / "style_factor_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
        return 0
    if args.command == "report" and args.report_command == "global-six-market":
        study_path = Path(args.study)
        study = _load_yaml(study_path)
        output = Path(str(study.get("output_root", "outputs/global_six_market")))
        run_global_six_market(study_path, output)
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
    if args.command == "report" and args.report_command == "smallcap-turnover":
        config = _load_config(Path(args.config))
        sources = config.get("sources", {})
        a_share_root = Path(str(sources.get("a_share_root", ""))) if isinstance(sources, dict) else Path("")
        if not a_share_root.exists():
            raise RuntimeError("A-share source is required for smallcap-turnover report")
        panel, metadata = build_a_share_panel(
            a_share_root,
            config.get("as_of") or None,
            use_duckdb=bool(config.get("use_duckdb", False)),
        )
        stats = build_smallcap_turnover_stats(panel)
        output_root = Path(config.get("output_root", "outputs"))
        output_root.mkdir(parents=True, exist_ok=True)
        stats.to_csv(output_root / "smallcap_turnover_daily.csv", index=False)
        summary = {
            "method": "daily smallest A-share stocks ranked by total market cap",
            "rank_counts": list(DEFAULT_RANK_COUNTS),
            "observations": int(len(stats)),
            "trading_days": int(stats["date"].nunique()) if not stats.empty else 0,
            "coverage_start": stats["date"].min() if not stats.empty else None,
            "coverage_end": stats["date"].max() if not stats.empty else None,
            "source": metadata.as_dict(),
            "caveats": [
                "当前清洗面板仅保留成交额和总市值均为正的观测。",
                "这是成交额描述性统计，不等同于策略容量或实际可成交金额。",
                "最小 N 只按当日总市值排序，不能直接用于无滞后的交易回测。",
            ],
        }
        (output_root / "smallcap_turnover_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        artifact = output_root / "smallcap_turnover_daily.csv"
        manifest = {
            "schema_version": "smallcap_turnover.v1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "method": summary["method"],
            "source": metadata.as_dict(),
            "coverage": {
                "start": summary["coverage_start"],
                "end": summary["coverage_end"],
                "trading_days": summary["trading_days"],
            },
            "artifacts": [
                {
                    "path": artifact.name,
                    "format": "csv",
                    "rows": int(len(stats)),
                    "bytes": artifact.stat().st_size,
                    "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                },
                {
                    "path": "smallcap_turnover_summary.json",
                    "format": "json",
                },
            ],
            "storage_policy": "full research output remains outside the Git repository; publish only reviewed derived summaries",
        }
        (output_root / "smallcap_turnover_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        return 0
    if args.command == "report" and args.report_command == "smallcap-turnover-history":
        config = _load_config(Path(args.config))
        section = config.get("smallcap_turnover_history", {})
        if not isinstance(section, dict):
            raise RuntimeError("smallcap_turnover_history must be a mapping")
        daily_root = Path(str(section.get("daily_root", "")))
        daily_basic_root = Path(str(section.get("daily_basic_root", "")))
        panel, metadata = load_historical_turnover_panel(
            daily_root,
            daily_basic_root,
            start_date=str(section["start_date"]) if section.get("start_date") else None,
            end_date=str(section["end_date"]) if section.get("end_date") else config.get("as_of") or None,
        )
        stats = build_smallcap_turnover_stats(panel)
        output_root = Path(config.get("output_root", "outputs"))
        output_root.mkdir(parents=True, exist_ok=True)
        daily_artifact = output_root / "smallcap_turnover_history_daily.csv"
        summary_artifact = output_root / "smallcap_turnover_history_summary.json"
        manifest_artifact = output_root / "smallcap_turnover_history_manifest.json"
        stats.to_csv(daily_artifact, index=False)
        summary = {
            "method": "historical daily smallest A-share stocks ranked by total market cap",
            "rank_counts": list(DEFAULT_RANK_COUNTS),
            "observations": int(len(stats)),
            "trading_days": int(stats["date"].nunique()) if not stats.empty else 0,
            "coverage_start": stats["date"].min() if not stats.empty else None,
            "coverage_end": stats["date"].max() if not stats.empty else None,
            "quality_status": metadata["quality_status"],
            "source": metadata,
            "caveats": [
                "2008 年起历史源没有可靠的 ST 和停牌字段，不能等同于 2015 年后清洗口径。",
                "历史报告只过滤成交额和总市值为正的观测。",
                "这是成交额描述性统计，不等同于策略容量或实际可成交金额。",
            ],
        }
        summary_artifact.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        manifest = {
            "schema_version": "smallcap_turnover_history.v1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "method": summary["method"],
            "source": metadata,
            "coverage": {"start": summary["coverage_start"], "end": summary["coverage_end"], "trading_days": summary["trading_days"]},
            "artifacts": [
                {"path": daily_artifact.name, "format": "csv", "rows": int(len(stats)), "bytes": daily_artifact.stat().st_size, "sha256": hashlib.sha256(daily_artifact.read_bytes()).hexdigest()},
                {"path": summary_artifact.name, "format": "json"},
            ],
            "storage_policy": "full research output remains outside the Git repository; publish only reviewed derived summaries",
        }
        manifest_artifact.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
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


def _load_yaml(path: Path) -> dict[str, object]:
    import yaml

    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ValueError(f"study config must be a mapping: {path}")
    return value


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
        market_cap_path = Path(str(sources["jp_market_cap_path"])) if sources.get("jp_market_cap_path") else None
        panels["jp"], metadata["jp"] = build_jp_panel(Path(str(sources["jp_root"])), as_of, market_cap_path=market_cap_path)
    return panels, metadata
