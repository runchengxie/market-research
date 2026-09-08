# Research Boundary Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 18 年风格因子研究的市场证据层和 `global_six_market` ETF proxy 配置研究迁入 `market-research`，同时在 `quant-research` 与 `quant-platform` 中明确保留边界、来源和 deprecated/redirect 关系。

**Architecture:** `market-research` 成为 market evidence 的 canonical research entry point；研究输入通过统一 panel/config/artifact contract 接入，原始数据和私有缓存留在外部资产目录；`quant-research` 保留 alpha/strategy 层；`quant-platform` 提供无观点的通用计算能力。实现按仓库和责任分成可审查的 PR，不跨仓库直接复制不明来源代码。

**Tech Stack:** Python 3.11+, pandas, PyYAML/TOML（以各仓库现有依赖为准）, pytest, existing web test/build toolchain, GitHub CLI/PR workflow.

**Spec:** `docs/superpowers/specs/2026-09-08-research-boundary-migration-design.md`

## Global Constraints

- [ ] 所有实现必须在独立 worktree 中完成；不在 `main` 上直接开发。
- [ ] 避开当前 `quant-research` 和 `research-workspace/quant-research` 的未提交用户改动，不 reset、checkout 或删除它们。
- [ ] 不提交原始数据、机器绝对路径、凭证、IBKR 下载缓存或大体量结果。
- [ ] 不复制许可证/来源未确认的 `portfolio_backtester` style-factor implementation；需要时做 clean reimplementation，并在 provenance 中记录依据。
- [ ] 不改变 `global_six_market` 当前 `exploration` 和 `production_eligible=false` 门禁。
- [ ] 先写失败测试再写实现；每个阶段都运行聚焦测试，再运行完整测试。
- [ ] 迁移完成后通过 PR 合并各仓库 main，再删除 branch 和 worktree；删除前保留 PR、commit 和 compatibility notice 作为历史记录。

## Task 1: Freeze the source inventory and ownership map

**Files:**
- Create: `market-research/docs/research-boundary-migration.md`
- Create: `market-research/docs/source-inventory-2026-09.md`
- Modify: `quant-research/README.md` and relevant `research/experiments/style_factors/README` or directory notice
- Modify: `quant-platform/README.md` and relevant research artifact documentation

**Interfaces / decisions:**
- A source-to-target table listing every candidate family, source path, target path, disposition (`migrate`, `retain`, `reimplement`, `archive`), and license/provenance status.
- Explicit distinction between “18-year inclusive window” and a study about calendar year 2018.
- Explicit statement that `global_six_market` is a six-ETF proxy allocation study, not a complete six-country equity universe or vendor-validation project.

- [ ] Audit source files in `quant-research` and `research-workspace/quant-research` without touching uncommitted files.
- [ ] Classify style-factor files into market evidence, alpha/strategy, generic computation, and unrelated experiments.
- [ ] Record the six-market source files (`README.md`, `experiment.yml`, `loader.py`, `portfolio.py`, `run.py`) and external data boundary.
- [ ] Record license uncertainty and prohibit direct copying where provenance is not confirmed.
- [ ] Add redirect/ownership notices; do not delete legacy source files.
- [ ] Review the inventory for accidental raw paths or user-specific identifiers.
- [ ] Commit docs in separate branches/PRs per affected repository.

## Task 2: Create the market-research study contracts and public layout

**Files:**
- Create: `market-research/studies/style_factors_18y/README.md`
- Create: `market-research/studies/style_factors_18y/study.yml`
- Create: `market-research/studies/style_factors_18y/methodology.md`
- Create: `market-research/studies/global_six_market/README.md`
- Create: `market-research/studies/global_six_market/study.yml`
- Modify: `market-research/README.md`, `configs/local.example.toml`, and compatibility docs

**Interfaces:**
- Style study config must define `study_id`, `window_years: 18`, universe, factor families, quantiles, holding period, rebalance calendar, lag policy, and evidence status.
- Global study config must preserve markets, proxy tickers, target weights, base currency, cost assumptions, data root indirection, paper-shadow flags, and lifecycle gates.
- Both study READMEs must define input contract, output contract, limitations, reproducibility command, and canonical/legacy source locations.

- [ ] Write config schemas and reject unknown or unsafe path forms where practical.
- [ ] Remove the current global study’s Windows-only data-root assumption from the public config; use an environment/local config path while preserving the external-data boundary.
- [ ] Document ETF proxy semantics, FX attribution, local calendar timing, dividend status, cost status, 37-month diagnostic limitation, and fixed-weight rationale as an explicit open research assumption.
- [ ] Add a compatibility table mapping old commands/files to new study entry points.
- [ ] Test config parsing with fixture configs and no real data.

## Task 3: Migrate/reimplement reusable style-market evidence

**Files:**
- Create: `market-research/src/market_research/style_portfolios/definitions.py`
- Create: `market-research/src/market_research/style_portfolios/cross_section.py`
- Create: `market-research/src/market_research/style_portfolios/diagnostics.py`
- Create: `market-research/src/market_research/style_portfolios/provenance.py`
- Create/modify: `market-research/tests/test_style_portfolios.py`, `tests/test_style_factor_study.py`

**Interfaces:**
- `build_quantile_returns(panel, factor_column, quantiles, holding_period, rebalance_frequency, universe_filter) -> DataFrame`
- `summarize_market_factor_evidence(quantile_returns, factor_name, metadata) -> dict`
- `analyze_tail_monotonicity(quantile_returns, direction, tail_quantiles) -> dict`
- `load_style_factor_artifact(root) -> StyleFactorArtifact`

The panel contract must require formation date, security identifier, factor value, forward return inputs, tradability/quality flags, and provenance. Outputs must include formation date, bucket, bucket label, return statistics, count, coverage, and exclusion counts. No alpha score, strategy recommendation, IC or decay result belongs in this module.

- [ ] Add fixtures with deliberately monotone small-to-large returns, reversed factor direction, missing values, ST/suspended rows, insufficient forward prices, and ties.
- [ ] Write failing tests for date alignment, no look-ahead, quantile ordering, tail spread, adjacent-sign monotonicity, and empty/insufficient samples.
- [ ] Implement the smallest clean-room reusable computation needed by the study; do not import `quant_research` or the unclear-license backtester.
- [ ] Add provenance fields for source artifact ID/hash, code version, as-of date, factor definition, lag, universe filter, calendar, and quality status.
- [ ] Reconcile the output against existing historical Barra artifacts only as a diagnostic; do not call historical five-quantile long-short output a newly computed ten-/twenty-quantile size monotonicity result.
- [ ] Run focused tests, full Python tests, and inspect generated output for paths/credentials.

## Task 4: Migrate the global six-market study

**Files:**
- Create: `market-research/src/market_research/studies/global_six_market/__init__.py`
- Create: `config.py`, `loader.py`, `portfolio.py`, `reporting.py`, `run.py`
- Create/modify: `market-research/tests/studies/test_global_six_market.py`
- Create: `market-research/studies/global_six_market/reports/README.md`

**Interfaces:**
- `load_daily_asset(path, market) -> DataFrame`
- `load_fx_series(path, currency) -> DataFrame`
- `load_distributions(path, market, currency) -> DataFrame`
- `validate_common_history(assets, fx, minimum_months=24) -> ValidationResult`
- `compute_usd_returns(asset, fx, calendar) -> DataFrame`
- `run_experiment(config_path, output_dir) -> RunSummary`

Behavior to preserve:

- US/HK/UK/AU/CA/SG weights 35/20/15/10/10/10;
- local month-end observation and next available trading-session execution;
- non-USD conversion using daily FX;
- missing/invalid proxy, missing FX, insufficient common history, missing dividends/costs, and incomplete paper-shadow ledger remain explicit gates;
- paper-shadow only; no order submission or IBKR execution adapter changes.

- [ ] First port tests from the existing global study to synthetic fixtures, preserving validation semantics rather than file layout.
- [ ] Add tests for duplicate dates, invalid prices/volume, missing FX, gaps over the allowed threshold, calendar mismatches, and common-history minimum.
- [ ] Add tests for local-return/FX-return decomposition and USD compounding.
- [ ] Add tests proving missing distributions cannot be silently labeled total return.
- [ ] Add tests proving the run writes no order or broker side effect.
- [ ] Implement config-relative path resolution and output manifests that contain hashes/IDs but no machine-local raw paths.
- [ ] Add a differential diagnostic against the known 2026-09-04 price-return run only when external artifacts are available; otherwise use synthetic expected values and report the comparison as unavailable.
- [ ] Keep lifecycle `exploration` until dividends, cost calibration, shadow review, and longer history gates are satisfied.

## Task 5: Add CLI and report integration

**Files:**
- Modify: `market-research/src/market_research/cli.py`
- Modify: `market-research/tests/test_cli.py`
- Modify: `market-research/README.md`, `docs/runbook-local.md`, `docs/data-contract.md`

**Interfaces:**
- `market-research report style-factors --study studies/style_factors_18y/study.yml`
- `market-research report global-six-market --study studies/global_six_market/study.yml`

Expected derived outputs:

- style study: `factor_summary.json`, quantile returns, tail monotonicity summary, exclusion/coverage table, source manifest;
- global study: `total_return_summary.json`, `dividend_attribution.csv`, `competition_metrics.csv`, `rebalance_ledger.csv`, `paper_shadow_ledger.csv`, decision/status manifest.

- [ ] Add parser and command failure tests before implementation.
- [ ] Implement commands as orchestration only; calculations stay in study/library modules.
- [ ] Ensure output metadata distinguishes `verified`, `derived`, `incomplete`, `not_comparable`, and `exploration`.
- [ ] Document that historical results can be read from external artifact roots and that raw data remains outside Git.
- [ ] Run focused CLI tests and full Python suite.

## Task 6: Decide and implement the web/public presentation layer

**Files:**
- Inspect and modify only after Tasks 2–5 are stable: `market-research/web/*`, snapshot data files, page tests, and build config.

**Design:** adopt the useful principles of `a-share-zoo-garden`—clear research cards, compact status badges, strong hierarchy, readable evidence tables, and visible caveats—without copying its project-specific content or assets. The page should expose study status and derived summaries, not raw data or unsupported performance claims.

- [ ] Compare existing `market-research` web structure with `a-share-zoo-garden` and write a small mapping of reusable visual patterns.
- [ ] Add pages/cards for Style Factors 18Y and Global Six-Market Allocation only if their snapshot contracts are stable.
- [ ] Show lifecycle/evidence status, sample window, proxy/FX/dividend/cost caveats, and provenance link near every headline metric.
- [ ] Add web tests for missing/incomplete snapshot states and build the site.
- [ ] Keep visual changes in a separate PR from core calculation migration if the diff is materially large.

## Task 7: Cross-repository boundary notices and legacy redirects

**Files:**
- Modify: `quant-research/README.md`, style-factor directory notices, and any command migration docs.
- Modify: `quant-platform/README.md` and research-contract docs.
- Modify: `market-research/docs/compatibility.md` and migration docs.

- [ ] Mark migrated market-evidence paths as legacy/deprecated with canonical `market-research` locations and removal policy.
- [ ] Mark alpha/strategy paths explicitly as retained in `quant-research`.
- [ ] Mark platform APIs explicitly as retained in `quant-platform`; remove any study-specific `RESEARCH_YEARS=18` policy from platform-facing code if found.
- [ ] Do not mark a source deprecated until the replacement has passed its tests and provenance review.
- [ ] Verify all README links and commands from a clean checkout.

## Task 8: Verification, review, merge, and cleanup

**Files:**
- No new implementation files; update changelogs/PR descriptions as needed.

- [ ] Run `pytest` and project-specific lint/type checks in `market-research`, `quant-research`, and `quant-platform` as applicable.
- [ ] Run web tests and production build in `market-research`.
- [ ] Run a repository-wide secret/path scan for raw data roots, credentials, and oversized files.
- [ ] Review diffs for accidental changes to the user’s pre-existing uncommitted files.
- [ ] Request code review before merging each implementation PR.
- [ ] Merge in dependency order: contracts/study docs, core market-research implementation, boundary notices, then optional web presentation.
- [ ] Update each local main from origin after merge.
- [ ] Delete merged local/remote branches and remove their worktrees only after PR merge is confirmed.
- [ ] Verify `git worktree list`, clean mains, and canonical README links as the final handoff.

## Proposed PR sequence

1. `market-research`: study contracts, source inventory, and style evidence library.
2. `market-research`: global six-market study port and CLI/report integration.
3. `quant-research`: ownership notices and redirects; preserve alpha/strategy work.
4. `quant-platform`: ownership/contract documentation and only genuinely generic API changes.
5. `market-research`: web presentation inspired by `a-share-zoo-garden`, if snapshot contracts are ready.

Each PR gets its own feature branch/worktree. No PR will delete the legacy source until the replacement and compatibility mapping are verified.

## Expected final result

完成后，用户看到的不是“几个目录被搬走”，而是一套可解释的边界：

- `market-research` 回答市场现象和跨市场组合事实；
- `quant-research` 回答 alpha/策略是否值得采用；
- `quant-platform` 提供三者共同使用的无观点计算能力；
- 所有旧路径都有明确的 canonical location、状态和 provenance。
