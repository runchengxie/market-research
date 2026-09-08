# Barra Factor Research Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 quant 中现有的 A 股 Barra/风格因子研究结果接入 market-research 的统一研究入口，并提供可复用的市值因子分位与尾部单调性诊断。

**Architecture:** 新增一个轻量的 `barra` 模块，负责读取已落盘的风格因子结果、标准化元数据并生成摘要；同一模块对 canonical A-share panel 执行按日期截面分位、未来收益和单调性统计。CLI 只编排输入输出，原始行情仍留在 quant 数据资产目录。

**Tech Stack:** Python 3.11+, pandas, DuckDB optional, pytest, TOML.

**Spec:** `docs/superpowers/specs/2026-09-07-market-research-design.md`

## Global Constraints

- 不将 quant 的原始行情、机器绝对路径或凭证复制进 market-research。
- 市值排序只使用形成日可见的 `market_cap`，收益使用下一交易日及后续形成日价格。
- 排除 ST、停牌、非正市值和无有效未来价格的样本，并在输出中记录覆盖与排除口径。
- 保留 quant 历史研究产物作为来源引用，不宣称它们已经完成纯市值十分位单调性检验。
- 新 CLI 和报告输出必须有测试覆盖；先写失败测试再实现。

### Task 1: Add Barra result contract and summary reader

**Files:**
- Create: `src/market_research/barra.py`
- Create: `tests/test_barra.py`

**Interfaces:**
- Produces `load_barra_summary(path: Path) -> dict[str, object]` for a quant style report directory.
- Produces `summarize_barra_factor_file(path: Path) -> dict[str, object]` for one `factor_*_daily.csv` file.

- [ ] Write failing tests for loading the report metadata, recognizing the size factor, and rejecting missing files.
- [ ] Run `pytest tests/test_barra.py -q` and observe the expected missing-function failure.
- [ ] Implement the minimal readers with explicit source path, report date, factor names, and size-factor summary.
- [ ] Run the focused tests and then the full Python test suite.
- [ ] Commit with `feat: add barra research result contract`.

### Task 2: Add pure size-factor quantile and tail monotonicity analysis

**Files:**
- Modify: `src/market_research/barra.py`
- Modify: `tests/test_barra.py`

**Interfaces:**
- Produces `analyze_size_monotonicity(panel: pd.DataFrame, quantiles: int = 10, holding_period: int = 1) -> tuple[pd.DataFrame, dict[str, object]]`.
- The returned table contains `formation_date`, `bucket`, `bucket_label`, `mean_forward_return`, `median_forward_return`, `count`; the summary contains `monotonicity_score`, `tail_spread`, `coverage_start`, and `coverage_end`.

- [ ] Add a fixture with deliberately monotone small-to-large returns and a fixture with invalid/ST/suspended rows.
- [ ] Run the focused tests and verify they fail because the analyzer is absent.
- [ ] Implement date-aligned forward returns, ascending market-cap buckets, adjacent-sign score, and tail spreads.
- [ ] Run focused tests, including one-day and multi-day holding periods.
- [ ] Commit with `feat: add size factor tail monotonicity diagnostics`.

### Task 3: Add CLI, configuration, and report outputs

**Files:**
- Modify: `src/market_research/cli.py`
- Modify: `configs/local.example.toml`
- Modify: `tests/test_cli.py`
- Modify: `README.md`
- Modify: `docs/runbook-local.md`

**Interfaces:**
- Add `market-research report barra --config PATH`.
- The command writes `barra_summary.json`, `barra_size_quantiles.csv`, and `barra_source_manifest.json` under `output_root`.
- Config keys are `[barra] result_root`, `size_quantiles`, and `holding_period`.

- [ ] Add a CLI test asserting the new parser command and output contract.
- [ ] Run the CLI test and verify it fails before implementation.
- [ ] Implement config loading, optional result-root summary, and A-share panel analysis.
- [ ] Document the command, result-root boundary, and caveats about the legacy quant report.
- [ ] Run all Python tests and a sample CLI invocation on a small fixture.
- [ ] Commit with `feat: expose barra research report command`.

### Task 4: Verify migration provenance and finish branch

**Files:**
- Create: `docs/barra-migration.md`
- Modify: `docs/compatibility.md`

- [ ] Record the quant source directory, migrated factor list, preserved artifacts, and known gap that historical pure-size quantile curves were not previously persisted.
- [ ] Run Python tests, web tests, and build.
- [ ] Inspect git diff and verify no raw data or machine-local result files entered the repository.
- [ ] Commit documentation with `docs: record barra research migration`.
- [ ] Use `finishing-a-development-branch` to present the branch for merge, then merge main and remove the branch/worktree as previously requested.
