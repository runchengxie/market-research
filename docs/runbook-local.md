# Local runbook

## Setup

```bash
uv sync --extra dev --extra duckdb
cp configs/local.example.toml configs/local.toml
```

Edit `configs/local.toml` so each source points to an existing local data root.
The file is ignored by Git because the paths are machine-specific.
Set `use_duckdb = true` for large A-share Parquet directories and install the
optional DuckDB dependency with `uv sync --extra duckdb`.

## Validate configured roots

```bash
uv run market-research validate --config configs/local.toml
```

This command only discovers configured roots and does not read all market data.

## Build liquidity report

```bash
uv run market-research report liquidity --config configs/local.toml
```

Outputs are written under `output_root`:

- `liquidity_report.json`
- `liquidity_summary.csv`
- `coverage_diagnostics.csv`

## Build A-share microcap reconstruction

```bash
uv run market-research report microcap --config configs/local.toml
```

The output is a research reconstruction of the smallest-400 equal-weight rule,
not the official Wind 8841431.WI index. It does not simulate costs, limit-up
execution, suspension execution, market impact, or strategy capacity.

## Known local roots

- A-share daily-clean data: `/home/richard/data/market-data-platform/assets/tushare/a_share/daily`
- HK RQData assets: `/mnt/data/cold4t/hk-liquidity/assets/rqdata/hk`
- US SimFin: `/mnt/data/cold4t/simfin/us/extracted/us-shareprices-daily.csv`
- JPX/J-Quants via nira: `/mnt/data/cold4t/nira/current/guan-japanese-nira/data`
