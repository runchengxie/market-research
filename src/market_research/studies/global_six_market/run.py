from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

from .loader import load_daily_asset, load_distributions, load_fx_series, validate_common_history
from .portfolio import compute_usd_return_components, summarize_portfolio


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_experiment(config_path: Path, output_dir: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    root = Path(config["data_root"]).expanduser()
    assets = {m: load_daily_asset(_resolve(root, p), m) for m, p in config["asset_files"].items()}
    fx = {c: load_fx_series(_resolve(root, p), c) for c, p in config.get("fx_files", {}).items()}
    distributions = {}
    for market, path_value in config.get("distribution_files", {}).items():
        path = _resolve(root, path_value)
        distributions[market] = load_distributions(path, market, {"US":"USD","HK":"HKD","UK":"GBP","AU":"AUD","CA":"CAD","SG":"SGD"}[market]) if path.is_file() else pd.DataFrame()
    history = validate_common_history(assets, fx)
    returns = compute_usd_return_components(assets, fx, distributions, config["target_weights"], config["costs_bps"])
    output_dir.mkdir(parents=True, exist_ok=True)
    status = "complete" if returns.attrs["total_return_status"] == "complete" else "unavailable"
    summary = {"schema_version": "global_six_market.summary.v1", "experiment_id": config["experiment_id"], "evidence_status": "exploration", "production_eligible": False, "history": history, "metrics": summarize_portfolio(returns), "total_return_status": status, "paper_shadow_complete": bool(config.get("paper_shadow_complete", False))}
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    returns.to_csv(output_dir / "rebalance_ledger.csv", index=False)
    (output_dir / "total_return_summary.json").write_text(json.dumps({"schema_version":"global_six_market.total_return_summary.v1", "total_return_status":status, "evidence_status":"exploration", "metrics":summary["metrics"] if status == "complete" else {}}, indent=2) + "\n", encoding="utf-8")
    inputs = [config_path, *(_resolve(root, p) for p in config["asset_files"].values()), *(_resolve(root, p) for p in config.get("fx_files", {}).values())]
    lock = {"schema_version": "global_six_market.inputs_lock.v1", "raw_data_copied": False, "inputs": [{"name": p.name, "sha256": _sha256(p)} for p in inputs if p.is_file()]}
    (output_dir / "inputs.lock.json").write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    return summary
