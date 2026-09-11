# market-research Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working `market-research` foundation that normalizes A-share, HK, US, and JP daily data, computes lagged liquidity/capacity diagnostics, and connects the A-share microcap reconstruction without copying raw data.

**Architecture:** Create a new Python package with explicit contracts, source adapters, liquidity features, capacity calculations, index reconstruction, and report snapshots. Keep `index-research`, `market-liquidity-profiles`, and `nira` unchanged; migrate behavior through tested implementations and read-only configured data roots.

**Tech Stack:** Python 3.11+, pandas, pyarrow, DuckDB for large CSV/Parquet scans, pytest, CSV/Parquet/JSON outputs, optional Markdown report generation.

**Spec:** `docs/superpowers/specs/2026-09-07-market-research-design.md`

## Global Constraints

- Do not copy raw market data into the Git repository.
- Do not modify or delete `index-research`, `market-liquidity-profiles`, or `nira` during the foundation migration.
- Every panel row uses `(market, symbol, date)` grain.
- ADV/MedADV features are lagged by one trading day and never use same-day turnover.
- Missing observations are not silently converted to zero turnover.
- Reports must record source, as-of date, coverage, universe filter, currency, FX method, feature lag, and quality status.
- Mechanical capacity is not strategy capacity and must be labeled accordingly.
- Use `apply_patch` for source edits and keep each task independently testable.

## Planned File Structure

```text
market-research/
├── pyproject.toml
├── .gitignore
├── README.md
├── configs/
│   └── local.example.toml
├── src/market_research/
│   ├── __init__.py
│   ├── contracts.py
│   ├── provenance.py
│   ├── quality.py
│   ├── markets/
│   │   ├── __init__.py
│   │   ├── a_share.py
│   │   ├── hk.py
│   │   ├── us.py
│   │   └── jp.py
│   ├── liquidity.py
│   ├── capacity.py
│   ├── indexes.py
│   ├── reports.py
│   └── cli.py
├── tests/
│   ├── test_contracts.py
│   ├── test_quality.py
│   ├── markets/
│   │   ├── test_a_share.py
│   │   ├── test_hk.py
│   │   ├── test_us.py
│   │   └── test_jp.py
│   ├── test_liquidity.py
│   ├── test_capacity.py
│   ├── test_indexes.py
│   └── test_reports.py
└── outputs/
```

### Task 1: Bootstrap the package and configuration contract

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `configs/local.example.toml`
- Create: `src/market_research/__init__.py`
- Create: `src/market_research/cli.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Produces an installable package named `market-research`.
- Produces CLI entry point `market-research` with `--help` and `config inspect`.
- Configuration fields: `a_share_root`, `hk_daily_root`, `hk_valuation_root`, `hk_instruments_path`, `us_shareprices_path`, `jp_root`, `output_root`, `as_of`.

- [ ] **Step 1: Write the failing CLI test**

```python
def test_cli_help_and_config_inspect(tmp_path):
    from market_research.cli import main

    assert main(["--help"]) == 0
    assert main(["config", "inspect", "--output-root", str(tmp_path)]) == 0
```

- [ ] **Step 2: Run the focused test**

Run: `pytest tests/test_cli.py -q`

Expected: FAIL because the package and CLI do not exist.

- [ ] **Step 3: Add minimal package metadata and CLI**

Define a console script named `market-research`, use `src/` layout, and make `config inspect` print JSON containing resolved paths without requiring any source data to exist.

- [ ] **Step 4: Run the focused test**

Run: `pytest tests/test_cli.py -q`

Expected: PASS.

- [ ] **Step 5: Document local data roots**

Document the known roots: `/home/richard/data/quant/market-data-platform/assets/tushare/a_share`, `/mnt/data/cold4t/hk-liquidity`, `/mnt/data/cold4t/simfin`, and `/mnt/data/cold4t/nira/current/guan-japanese-nira/data`. State that the example config contains no credentials. Add `.gitignore` rules for `configs/local.toml`, `outputs/`, `.venv/`, caches, and raw market-data extensions.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml README.md configs src tests
git commit -m "feat: bootstrap market research package"
```

### Task 2: Define the canonical panel and provenance metadata

**Files:**
- Create: `src/market_research/contracts.py`
- Create: `src/market_research/provenance.py`
- Create: `src/market_research/quality.py`
- Create: `tests/test_contracts.py`
- Create: `tests/test_quality.py`

**Interfaces:**
- `PanelMetadata` dataclass with `source`, `as_of`, `currency`, `universe_filter`, `fx_method`, `feature_lag`, `coverage_start`, `coverage_end`, `calendar_mode`, `quality_status`.
- `CANONICAL_COLUMNS` tuple containing `market`, `symbol`, `date`, `close`, `volume`, `turnover`, `market_cap`, `currency`, `is_tradable`, `is_suspended`, `source`.
- `normalize_panel(frame: pd.DataFrame, metadata: PanelMetadata) -> tuple[pd.DataFrame, PanelMetadata]`.
- `validate_panel(frame: pd.DataFrame) -> list[str]` returning deterministic issue codes.
- `write_provenance(path: Path, metadata: PanelMetadata, command: str) -> None`.

- [ ] **Step 1: Write contract and validation tests**

Cover canonical column ordering, date coercion, duplicate `(market, symbol, date)` rejection, invalid currency rejection, non-finite numeric rejection, and preservation of missing observations.

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_contracts.py tests/test_quality.py -q`

Expected: FAIL because contract types and validators do not exist.

- [ ] **Step 3: Implement contract normalization**

Normalize dates to timezone-naive dates, preserve source units in `currency`, reject duplicate keys, and require metadata fields before returning a panel.

- [ ] **Step 4: Implement provenance serialization**

Serialize metadata, input paths, command, package version, and schema version to stable sorted JSON.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_contracts.py tests/test_quality.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/market_research/contracts.py src/market_research/provenance.py src/market_research/quality.py tests/test_contracts.py tests/test_quality.py
git commit -m "feat: add canonical market panel contract"
```

### Task 3: Implement A-share, HK, and US adapters

**Files:**
- Create: `src/market_research/markets/__init__.py`
- Create: `src/market_research/markets/a_share.py`
- Create: `src/market_research/markets/hk.py`
- Create: `src/market_research/markets/us.py`
- Create: `tests/markets/test_a_share.py`
- Create: `tests/markets/test_hk.py`
- Create: `tests/markets/test_us.py`

**Interfaces:**
- `build_a_share_panel(data_root: Path, as_of: str | None = None, fx_rate: float | None = None) -> tuple[pd.DataFrame, PanelMetadata]`.
- `build_hk_panel(daily_root: Path, valuation_root: Path, instruments_path: Path, as_of: str | None = None, fx_rate: float | None = None) -> tuple[pd.DataFrame, PanelMetadata]`.
- `build_us_panel(source_path: Path, as_of: str | None = None) -> tuple[pd.DataFrame, PanelMetadata]`.

- [ ] **Step 1: Create fixture inputs**

Use tiny in-memory or temporary Parquet/CSV fixtures that include unit-bearing fields and one excluded ST/suspended/zero-volume row per market.

- [ ] **Step 2: Write failing adapter tests**

Assert A-share `amount * 1000`, `total_mv * 10000`, HK turnover and valuation conversion, US `Close * Volume`, positive market caps, and explicit metadata filters.

- [ ] **Step 3: Run focused tests**

Run: `pytest tests/markets/test_a_share.py tests/markets/test_hk.py tests/markets/test_us.py -q`

Expected: FAIL because adapters do not exist.

- [ ] **Step 4: Migrate adapter behavior**

Port the tested behavior from `market-liquidity-profiles/capacity/adapters.py` while routing every result through `normalize_panel`. Keep large SimFin reads on DuckDB when file size exceeds the existing threshold.

- [ ] **Step 5: Add source coverage diagnostics**

Record total rows, accepted rows, excluded rows, missing required columns, and date coverage in metadata or a quality result without turning missing rows into zeros.

- [ ] **Step 6: Run focused tests**

Run: `pytest tests/markets/test_a_share.py tests/markets/test_hk.py tests/markets/test_us.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/market_research/markets tests/markets
git commit -m "feat: add A-share HK and US panel adapters"
```

### Task 4: Add the JPX/J-Quants adapter from nira

**Files:**
- Create: `src/market_research/markets/jp.py`
- Create: `tests/markets/test_jp.py`
- Modify: `configs/local.example.toml`
- Modify: `README.md`

**Interfaces:**
- `build_jp_panel(data_root: Path, as_of: str | None = None, fx_rate: float | None = None) -> tuple[pd.DataFrame, PanelMetadata]`.
- `discover_jp_daily_files(data_root: Path) -> list[Path]`.

- [ ] **Step 1: Inspect representative JPX schemas**

Use DuckDB or PyArrow against one `data/daily/*/equities_bars_daily_*.parquet` and one `data/master/*/equities_master_*.csv` file. Record the exact field names used for code, date, close, volume, turnover, market cap or shares, and listing status in the adapter test fixture.

- [ ] **Step 2: Write failing JP adapter tests**

Cover JPY currency, code normalization, daily turnover mapping, master status filtering, as-of cutoff, and a missing-turnover case that remains missing rather than becoming zero.

- [ ] **Step 3: Run focused tests**

Run: `pytest tests/markets/test_jp.py -q`

Expected: FAIL because the JP adapter does not exist.

- [ ] **Step 4: Implement schema-tolerant JP adapter**

Read only the needed daily and master columns, join by stable code/date semantics, emit native JPY values, and mark unavailable market cap or turnover as missing with a quality warning. Do not use minute or trade data in this adapter.

- [ ] **Step 5: Add live local smoke test command**

Add a documented command that discovers the nira data root and prints row counts/date bounds without writing outputs.

- [ ] **Step 6: Run tests and smoke check**

Run: `pytest tests/markets/test_jp.py -q`

Expected: PASS. Then run the documented smoke command against `/mnt/data/cold4t/nira/current/guan-japanese-nira/data` and confirm it reports non-empty daily data.

- [ ] **Step 7: Commit**

```bash
git add src/market_research/markets/jp.py tests/markets/test_jp.py configs/local.example.toml README.md
git commit -m "feat: add JPX daily panel adapter"
```

### Task 5: Build lagged liquidity features and capacity surfaces

**Files:**
- Create: `src/market_research/liquidity.py`
- Create: `src/market_research/capacity.py`
- Create: `tests/test_liquidity.py`
- Create: `tests/test_capacity.py`

**Interfaces:**
- `add_lagged_liquidity(panel: pd.DataFrame, windows: tuple[int, ...] = (20, 60)) -> pd.DataFrame`.
- `build_capacity_surface(panel: pd.DataFrame, participation_rates: tuple[float, ...], horizons: tuple[int, ...]) -> pd.DataFrame`.
- `build_instrument_capacity(panel: pd.DataFrame, participation_rates: tuple[float, ...], horizons: tuple[int, ...]) -> pd.DataFrame`.

- [ ] **Step 1: Write failing liquidity tests**

Use a three-symbol, six-date fixture and assert that the first complete window is missing, date `t` uses turnover through `t-1`, and market boundaries do not mix.

- [ ] **Step 2: Run focused tests**

Run: `pytest tests/test_liquidity.py -q`

Expected: FAIL.

- [ ] **Step 3: Implement lagged ADV/MedADV**

Group by `(market, symbol)`, sort by date, shift one observation before rolling, and use `min_periods=window`. Preserve `is_tradable` and missing rows.

- [ ] **Step 4: Write failing capacity tests**

Assert `daily_capacity = participation_rate * lagged_liquidity`, `horizon_capacity = daily_capacity * horizon`, zero capacity for non-tradable rows, and explicit quality values for missing/zero liquidity.

- [ ] **Step 5: Implement capacity surfaces**

Port the mechanical formulas and lower-tail diagnostics from `market-liquidity-profiles/capacity`, retaining market/date/bucket counts, tradable coverage, quantiles, top-10 share, and HHI. Name the result `mechanical_capacity` in documentation and output metadata.

- [ ] **Step 6: Run focused tests**

Run: `pytest tests/test_liquidity.py tests/test_capacity.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/market_research/liquidity.py src/market_research/capacity.py tests/test_liquidity.py tests/test_capacity.py
git commit -m "feat: add lagged liquidity and capacity surfaces"
```

### Task 6: Migrate the A-share microcap reconstruction

**Files:**
- Create: `src/market_research/indexes.py`
- Create: `tests/test_indexes.py`
- Modify: `README.md`

**Interfaces:**
- `reconstruct_smallest_cap_index(panel: pd.DataFrame, constituent_count: int = 400) -> pd.DataFrame`.
- `summarize_nav(nav: pd.DataFrame) -> dict[str, object]`.
- `build_underwater_periods(nav: pd.DataFrame) -> pd.DataFrame`.

- [ ] **Step 1: Write regression fixtures from index-research**

Create a small deterministic panel with market caps, adjusted closes, ST/suspension flags, and next-day dates. Encode the expected selected count, daily return, NAV, and underwater episode.

- [ ] **Step 2: Run focused tests**

Run: `pytest tests/test_indexes.py -q`

Expected: FAIL.

- [ ] **Step 3: Port the microcap rule**

Use the existing rule: Shanghai/Shenzhen equities, exclude ST/suspended, rank by total market cap on date `t`, select the smallest 400, equal weight, and calculate next-trading-day adjusted-close returns only when the next stock date equals the next market date.

- [ ] **Step 4: Add liquidity-aware output columns**

Join lagged `medadv20`, `is_tradable`, and capacity fields by `(market, symbol, date)` without changing the return calculation. Report selected count, priced count, excluded count, and missing-liquidity count.

- [ ] **Step 5: Run regression tests**

Run: `pytest tests/test_indexes.py -q`

Expected: PASS and equal results for the fixture-based reconstruction.

- [ ] **Step 6: Commit**

```bash
git add src/market_research/indexes.py tests/test_indexes.py README.md
git commit -m "feat: connect microcap reconstruction to canonical panel"
```

### Task 7: Create cross-market report outputs

**Files:**
- Create: `src/market_research/reports.py`
- Create: `tests/test_reports.py`
- Modify: `src/market_research/cli.py`

**Interfaces:**
- `build_liquidity_report(panels: dict[str, pd.DataFrame], metadata: dict[str, PanelMetadata]) -> dict[str, object]`.
- `write_report_bundle(report: dict[str, object], output_root: Path) -> None`.
- CLI command: `market-research report liquidity --config configs/local.toml`.

- [ ] **Step 1: Write failing report tests**

Assert stable market ordering, market-cap buckets, median/mean/P90 turnover, lower-tail counts, metadata status, and JSON/CSV output paths.

- [ ] **Step 2: Run focused tests**

Run: `pytest tests/test_reports.py -q`

Expected: FAIL.

- [ ] **Step 3: Implement report aggregation**

Generate `liquidity_summary.csv`, `liquidity_report.json`, `capacity_surface.csv`, `coverage_diagnostics.csv`, and `provenance.json`. Keep native-currency and USD-normalized values separate.

- [ ] **Step 4: Implement partial-market behavior**

If a source is unavailable, emit a structured `incomplete` market result and continue other markets. Fail only when no market produces a valid panel or when a required schema is invalid.

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_reports.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/market_research/reports.py src/market_research/cli.py tests/test_reports.py
git commit -m "feat: generate cross-market liquidity reports"
```

### Task 8: Wire the end-to-end command and local smoke run

**Files:**
- Modify: `src/market_research/cli.py`
- Modify: `configs/local.example.toml`
- Modify: `README.md`
- Create: `tests/test_end_to_end.py`

**Interfaces:**
- CLI command: `market-research report liquidity --config <path>`.
- CLI command: `market-research report microcap --config <path>`.
- CLI command: `market-research validate --config <path>`.

- [ ] **Step 1: Write failing end-to-end test**

Use fixture roots for all four markets, run the liquidity command, and assert the report bundle plus provenance files exist and can be parsed.

- [ ] **Step 2: Run focused test**

Run: `pytest tests/test_end_to_end.py -q`

Expected: FAIL.

- [ ] **Step 3: Create the local runtime config**

Create `configs/local.toml` from the example with the discovered local paths. Keep it ignored by Git because paths are machine-specific. The committed `configs/local.example.toml` remains the portable template.

- [ ] **Step 4: Implement command orchestration**

Load config, discover available source roots, build panels, run quality checks, add lagged features, build capacity surfaces, and write the report bundle. Preserve command and source metadata.

- [ ] **Step 5: Add microcap command**

Build the A-share panel, run the smallest-400 reconstruction, and write `microcap_nav.csv`, `microcap_summary.json`, and `microcap_underwater_periods.csv` with the research-reconstruction caveat.

- [ ] **Step 6: Run fixture end-to-end test**

Run: `pytest tests/test_end_to_end.py -q`

Expected: PASS.

- [ ] **Step 7: Run local read-only smoke tests**

Run against the known paths:

```bash
uv run --project /home/richard/code/market-research market-research validate --config configs/local.toml
uv run --project /home/richard/code/market-research market-research report liquidity --config configs/local.toml
```

Expected: no raw files are created or modified; outputs are written only under the configured output root, and missing sources are reported explicitly.

- [ ] **Step 8: Commit**

```bash
git add src tests configs README.md
git commit -m "feat: add end-to-end market research commands"
```

### Task 9: Full verification and handoff documentation

**Files:**
- Modify: `README.md`
- Create: `docs/data-contract.md`
- Create: `docs/runbook-local.md`
- Create: `docs/compatibility.md`

- [ ] **Step 1: Run all tests**

Run: `pytest -q`

Expected: PASS with no changes to the legacy repositories.

- [ ] **Step 2: Compare A-share regression outputs**

Run the new microcap command and the existing `index-research/build_microcap_reconstruction.py` against the same local daily-clean snapshot. Compare coverage, selected count, daily returns, NAV, and maximum drawdown; document any intentional difference from metadata or feature joins.

- [ ] **Step 3: Run source quality checks**

Verify duplicate keys, date bounds, missingness, units, FX metadata, lagged feature behavior, and output provenance for all available markets.

- [ ] **Step 4: Document compatibility**

State that old projects remain the source of historical behavior until migration parity is confirmed, and provide commands for reproducing both old and new outputs.

- [ ] **Step 5: Commit**

```bash
git add README.md docs
git commit -m "docs: add market research runbooks and compatibility notes"
```

## Final Verification Checklist

- [ ] `pytest -q` passes in `market-research`.
- [ ] Four market adapters either produce valid panels or explicit `incomplete` results.
- [ ] No raw market data is tracked by Git.
- [ ] All rolling liquidity metrics are one trading day lagged.
- [ ] Missing observations are not silently treated as zero.
- [ ] A-share microcap regression is reproducible against `index-research`.
- [ ] Capacity output is explicitly labeled mechanical rather than investible strategy capacity.
- [ ] JPX data is read from the nira backup without modifying nira.
- [ ] Existing repositories remain clean and runnable.
