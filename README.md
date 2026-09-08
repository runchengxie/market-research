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

The JP adapter currently consumes only `daily/*/equities_bars_daily_*.parquet`.
It maps J-Quants `Date`, `Code`, `C`, `Vo`, and `Va` to the canonical panel.
The current nira snapshot does not provide a paired daily market-cap field, so
JP reports mark market-cap-dependent analysis as incomplete until that source
is added.

The architecture and migration scope are documented in
`docs/superpowers/specs/2026-09-07-market-research-design.md`.

The first report bundle contains a liquidity summary, coverage diagnostics,
lagged liquidity-based mechanical capacity surface, and provenance metadata.

## GitHub Pages

The public research snapshot is built from derived files only. It does not
publish raw market data, machine-specific paths, or credentials. To run the
dashboard locally:

```bash
cd web
npm ci
npm run dev
```

Pushing to `main` runs the web tests and build, then deploys the static site to
`https://runchengxie.github.io/market-research/` when GitHub Pages is enabled
with the GitHub Actions source.
