from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "web" / "public" / "data"
INDEX_ROOT = Path("/home/richard/code/index-research/web/public/outputs")
ANIMAL_ROOT = Path("/home/richard/code/a-share-animal-index/web/public/data")


INDEX_FILES = (
    "a_share_index_price_returns.csv",
    "etf_proxy_returns.csv",
    "index_catalog.csv",
    "index_api_probe.csv",
    "microcap/annual_returns.csv",
    "microcap/nav.csv",
    "microcap/reconstructed_daily_nav.csv",
    "microcap/reconstructed_summary.json",
    "microcap/reconstructed_underwater_periods.csv",
    "microcap/rolling_cagr.csv",
    "microcap/rolling_drawdown.csv",
    "microcap/source_notes.json",
    "microcap/summary.json",
    "cashflow_indices/cashflow_data_status.csv",
    "cashflow_indices/cashflow_performance.csv",
    "cashflow_indices/cashflow_rebalance_frequency.csv",
    "linked_indices/etf_index_pairing.csv",
    "linked_indices/linked_index_catalog.csv",
    "linked_indices/linked_index_fetch_status.csv",
    "linked_indices/paired_index_etf_representatives.csv",
    "linked_indices/paired_index_etf_returns_all.csv",
    "linked_indices/ten_year_price_returns.csv",
)


def copy_files(source_root: Path, target_root: Path, files: tuple[str, ...]) -> int:
    copied = 0
    for relative in files:
        source = source_root / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied += 1
    return copied


def main() -> None:
    if not INDEX_ROOT.exists():
        raise SystemExit(f"missing index-research public output: {INDEX_ROOT}")
    if not ANIMAL_ROOT.exists():
        raise SystemExit(f"missing a-share-animal-index public data: {ANIMAL_ROOT}")

    copied = copy_files(INDEX_ROOT, TARGET / "index", INDEX_FILES)
    for relative in (
        "latest.json",
        "history.json",
        "metadata.json",
        "changes.json",
        "constituents.json",
    ):
        copy_files(ANIMAL_ROOT, TARGET / "animal", (relative,))
        copy_files(ANIMAL_ROOT / "plant", TARGET / "plant", (relative,))
        copied += 2

    manifest_path = TARGET / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["included_snapshots"] = {
        "index_research_files": copied - 10,
        "animal_index_variants": ["animal", "plant"],
        "raw_data_published": False,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"copied {copied} derived public snapshot files into {TARGET}")


if __name__ == "__main__":
    main()
