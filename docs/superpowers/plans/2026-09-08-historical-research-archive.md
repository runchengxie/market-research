# Historical Research Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将网页从“未来策略探索”叙事整理为以历史研究档案、描述性证据和研究状态为核心的入口，并修正市值分位诊断的分箱偏差。

**Architecture:** 保留现有四个研究域，但新增研究生命周期标签：历史研究、研究中、待补数据。历史研究页面读取已发布的派生快照；研究边界和统计限制放在底部 fine print。Barra 分位计算使用等频排名，避免最大市值组退化为单只股票。

**Tech Stack:** Python, pandas, React, TypeScript, Vite, Node test runner, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-09-08-research-ia-cross-market-smallcap-ui-design.md`

## Global Constraints

- 原始行情和外部研究资产不复制进仓库。
- 历史结果、当前重算结果和未来研究不得混称为统计显著结论。
- 日频横截面观测不自动视为独立样本；页面使用“描述性证据”措辞。
- 所有发布快照必须保留来源、覆盖区间和研究边界。

### Task 1: 修正市值分位诊断

**Files:**
- Modify: `src/market_research/barra.py`
- Test: `tests/test_barra.py`

- [ ] Add a regression test asserting equal-size buckets for a ten-stock cross-section.
- [ ] Replace floor-based bucket assignment with capped ceiling of percentile rank times quantiles.
- [ ] Run `uv run pytest tests/test_barra.py -q`.

### Task 2: Regenerate and publish the corrected Barra snapshot

**Files:**
- Create: `web/public/data/barra/barra_summary.json`
- Create: `web/public/data/barra/barra_size_quantiles.csv`
- Create: `web/public/data/barra/barra_source_manifest.json`

- [ ] Run the Barra report against the current A-share daily-clean path and external historical result bundle.
- [ ] Verify Q10 contains a normal cross-section count rather than one observation per date.
- [ ] Publish only derived JSON/CSV outputs.

### Task 3: Reframe the web information architecture

**Files:**
- Modify: `web/src/main.tsx`
- Modify: `web/src/styles.css`
- Modify: `web/src/editorialUi.test.mjs`

- [ ] Rename the masthead to a historical research archive framing.
- [ ] Add lifecycle/status labels for historical, descriptive, in-progress, and pending-data studies.
- [ ] Keep research notes in the reading flow, but move boundary warnings into low-emphasis fine print.
- [ ] Update Barra copy to distinguish historical result-package evidence from the current reproducible window.
- [ ] Add tests for the archive labels and non-significance wording.

### Task 4: Document the archive taxonomy and verify

**Files:**
- Modify: `README.md`
- Modify: `docs/research-information-architecture.md`
- Modify: `docs/barra-migration.md`

- [ ] Document the historical/ongoing/future research taxonomy and the difference between descriptive evidence and strategy validation.
- [ ] Run `uv run pytest -q`, `npm test`, `npm run build`, and `git diff --check`.
- [ ] Commit, push, merge to `main`, and remove the worktree and branch.
