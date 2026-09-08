# Complete Project Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended) or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all reusable research behavior and public outputs from `index-research` and `market-liquidity-profiles` into `market-research`, while retaining the old repositories as unchanged legacy archives.

**Architecture:** Keep `market-research` as the sole canonical Python package and web entry point. Add focused modules for index snapshots, ETF/index pairing, cash-flow index analysis, legacy liquidity analyses, and compatibility regression; route all filesystem access through the existing configuration and canonical panel contracts. Preserve the old repositories and compare their deterministic functions and fixture outputs against the new implementations.

**Tech Stack:** Python 3.11+, pandas, pyarrow, DuckDB, pytest, TOML configuration, TypeScript/Vite web build, CSV/Parquet/JSON derived artifacts.

**Spec:** `docs/superpowers/specs/2026-09-07-market-research-design.md`

## Global Constraints

- Do not delete or modify source files in `index-research`, `market-liquidity-profiles`, or `nira`.
- Do not copy raw market data or credentials into Git.
- Preserve native-currency values and record FX assumptions separately.
- Preserve the one-trading-day lag for liquidity features.
- Treat missing observations as missing/quality issues, never as zero turnover.
- Label capacity as a mechanical upper-bound diagnostic, not investible strategy capacity.
- Every new behavior starts with a failing focused test and is implemented with the smallest change that passes it.
- Use `apply_patch` for source and test edits.

### Task 1: Migrate reusable microcap snapshot analytics

**Files:**
- Create: `src/market_research/microcap.py`
- Create: `tests/test_microcap.py`
- Modify: `src/market_research/cli.py`

**Interfaces:**
- `calculate_annual_returns(nav: pd.DataFrame) -> pd.DataFrame`
- `calculate_rolling_cagr(nav: pd.DataFrame, windows: tuple[int, ...] = (1, 3, 5, 10, 15)) -> pd.DataFrame`
- `calculate_rolling_drawdown(nav: pd.DataFrame, windows: tuple[int, ...] = (1, 3, 5, 10, 15)) -> pd.DataFrame`
- `write_microcap_snapshot(nav: pd.DataFrame, output_root: Path, source_label: str) -> None`

- [ ] Write failing tests using the same NAV rows and expected annual/CAGR/drawdown values as `index-research/build_microcap_snapshot.py`.
- [ ] Run `uv run pytest tests/test_microcap.py -q` and confirm failure because the module is absent.
- [ ] Implement the functions with stable date ordering, explicit empty-window behavior, and the legacy output column names.
- [ ] Add `report microcap` output for `nav.csv`, `annual_returns.csv`, `rolling_cagr.csv`, `rolling_drawdown.csv`, `summary.json`, and underwater periods through the new writer.
- [ ] Run the focused tests and the existing index tests.
- [ ] Commit with `feat: migrate microcap snapshot analytics`.

### Task 2: Migrate index, ETF pairing, and cash-flow research APIs

**Files:**
- Create: `src/market_research/index_research.py`
- Create: `tests/test_index_research.py`
- Modify: `src/market_research/cli.py`
- Modify: `configs/local.example.toml`

**Interfaces:**
- `build_index_price_snapshot(index_daily: pd.DataFrame, as_of: str | None = None) -> pd.DataFrame`
- `match_index_name(benchmark: str, index_names: list[str]) -> str | None`
- `build_etf_index_pairing(etf_basic: pd.DataFrame, index_catalog: pd.DataFrame) -> pd.DataFrame`
- `build_cashflow_snapshot(raw: pd.DataFrame, indexes: tuple[dict[str, str], ...]) -> dict[str, pd.DataFrame]`

- [ ] Write failing tests for price-return endpoint selection, longest benchmark-name matching, cash-flow windows, and explicit price-vs-total-return status.
- [ ] Run `uv run pytest tests/test_index_research.py -q` and confirm the expected missing-API failure.
- [ ] Port the pure transformations from `analyze.py`, `pair_and_rank.py`, and `analyze_cashflow.py`; keep network fetching out of the core functions.
- [ ] Add config-driven commands `report indices` and `report cashflow` that write the legacy-compatible CSV snapshot names under the configured output root.
- [ ] Run focused tests and verify deterministic output under shuffled input rows.
- [ ] Commit with `feat: migrate index and cashflow research`.

### Task 3: Migrate legacy liquidity analyses and capacity compatibility

**Files:**
- Create: `src/market_research/liquidity_profiles.py`
- Create: `tests/test_liquidity_profiles.py`
- Modify: `src/market_research/reports.py`
- Modify: `src/market_research/cli.py`

**Interfaces:**
- `build_bucket_summary(panel: pd.DataFrame, currency: str = "native") -> pd.DataFrame`
- `build_cross_market_summary(panels: dict[str, pd.DataFrame], fx_rates: dict[str, float]) -> pd.DataFrame`
- `build_instrument_diagnostics(panel: pd.DataFrame) -> pd.DataFrame`

- [ ] Write failing tests for market-cap buckets, native/USD turnover separation, lower-tail counts, and the Aili-style rank diagnostic.
- [ ] Run `uv run pytest tests/test_liquidity_profiles.py -q` and confirm failure.
- [ ] Implement the old three-market formulas on canonical panels, reusing `add_lagged_liquidity` and the existing mechanical capacity model.
- [ ] Add the outputs to `report liquidity`, including explicit `quality_status`, `currency`, `fx_method`, and mechanical-capacity labels.
- [ ] Run focused tests and all existing liquidity/capacity tests.
- [ ] Commit with `feat: migrate liquidity profile analyses`.

### Task 4: Add complete configured orchestration and public snapshot builds

**Files:**
- Modify: `src/market_research/cli.py`
- Modify: `src/market_research/reports.py`
- Create: `tests/test_migration_commands.py`
- Modify: `web/scripts/build-public-snapshot.mjs`
- Modify: `web/src/main.tsx`
- Modify: `web/src/data.test.mjs`

**Interfaces:**
- CLI commands: `report indices`, `report cashflow`, `report liquidity`, `report microcap`, `validate`.
- Public snapshot namespaces: `index/`, `liquidity/`, and `provenance/`.

- [ ] Write failing command tests that exercise all report subcommands with temporary fixtures and assert every migrated artifact exists.
- [ ] Run the focused command tests and confirm failure for the new subcommands/artifacts.
- [ ] Implement orchestration with partial-source `incomplete` results, deterministic output ordering, and no writes outside the configured output/public snapshot roots.
- [ ] Add or update web tests so each migrated research tab consumes the canonical snapshot and displays its data-quality caveat.
- [ ] Run Python tests plus `cd web && npm ci && npm test && npm run build`.
- [ ] Commit with `feat: expose complete migrated research reports`.

### Task 5: Cross-project regression, documentation, and legacy handoff

**Files:**
- Create: `tests/test_legacy_regression.py`
- Modify: `README.md`
- Modify: `docs/compatibility.md`
- Modify: `docs/data-contract.md`
- Modify: `docs/runbook-local.md`
- Modify: `index-research/README.md` is forbidden; verify it remains unchanged.
- Modify: `market-liquidity-profiles/README.md` is forbidden; verify it remains unchanged.

- [ ] Write regression tests for all deterministic old-project transformations and compare canonical columns and values, allowing only documented metadata/format differences.
- [ ] Run both old-project test suites and the new full suite; install dependencies in each repo if required without changing tracked files.
- [ ] Run configured read-only smoke tests for every available local market source.
- [ ] Document the migrated command matrix, output mapping, known intentional differences, and canonical/superseding status.
- [ ] Verify `git status --short` is clean in both legacy repositories and no raw data is tracked in the new repository.
- [ ] Run `uv run pytest -q` and `cd web && npm test && npm run build` one final time.
- [ ] Commit with `docs: finalize legacy migration handoff`.

## Final Verification Checklist

- [ ] All reusable runnable behavior from both old projects has a `market-research` API or command.
- [ ] All old public output families have canonical generated equivalents.
- [ ] Cross-project regression tests pass or document a concrete intentional difference.
- [ ] Four markets produce valid or explicitly `incomplete` results.
- [ ] Existing legacy repositories are unchanged and runnable.
- [ ] `market-research` README and compatibility docs state canonical/superseding status.
- [ ] Python and web tests/builds pass.
