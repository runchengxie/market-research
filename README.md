# market-research

Cross-market equity research, liquidity, capacity, and index replication framework.

The project is intentionally local-first. It reads existing market-data assets
without copying raw files into the repository. The first supported markets are
A-share, Hong Kong, US, and Japan equities.

## Local setup

```bash
uv sync --extra dev --extra duckdb
cp configs/local.example.toml configs/local.toml
uv run market-research --help
uv run market-research config inspect --output-root outputs
```

The local configuration contains machine-specific data roots and is ignored by
Git. Do not put credentials in it.

Known local data roots include:

- A-share: `/home/richard/data/market-data-platform/assets/tushare/a_share`
- HK: `/mnt/data/cold4t/hk-liquidity`
- US: `/mnt/data/cold4t/simfin`
- JP: `/mnt/data/cold4t/nira/current/guan-japanese-nira/data`

The architecture and migration scope are documented in
`docs/superpowers/specs/2026-09-07-market-research-design.md`.
