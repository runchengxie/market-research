# Research IA, Cross-Market Small-Cap Liquidity, and UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `market-research` 整理为“现金流策略探索 / 小微盘策略探索 / 市场长期风格研究 / 跨市场探索”四类入口，完成 A 股与跨市场小微盘流动性对齐，利用 HK cold data 和 Japanese NIRA 生成真实历史比较，并完成总览页、导航、时间筛选和中文化 UI。

**Architecture:** Python 报告层负责从 A 股、港股 cold data、美股和 Japanese NIRA 生成统一的跨市场小微盘流动性快照；Web 只消费脱敏派生数据。小微盘域包含“A股小微盘”和“跨市场小微盘”两个 sub tab；市场长期风格域承载指数/ETF 长期表现、Barra 和 18 年因子市场证据；跨市场域承载更宽的市场流动性、Global Six-Market、FX 和分散化研究。

**Tech Stack:** Python 3.11+, pandas, DuckDB optional, pytest, React/TypeScript, Vite, Node test runner, CSS.

**Spec:** `docs/superpowers/specs/2026-09-08-research-ia-cross-market-smallcap-ui-design.md`

## Global Constraints

- [ ] 所有实现使用独立 worktree，不直接在 `main` 开发。
- [ ] 使用硬盘盒数据作为真实输入：HK `/mnt/data/cold4t/hk-liquidity`，Japanese NIRA `/mnt/data/cold4t/nira/current/guan-japanese-nira/data`；A 股和美股沿用现有配置路径。
- [ ] 不把原始行情、机器路径、凭证、损坏 Parquet 或大体量历史结果提交到 Git。
- [ ] 只有真实共同覆盖且达到 lagged ADV20 最低观测要求的区间才能标记 `verified`。
- [ ] 历史比较按每个市场、每个日期重新计算市值分桶，不使用当前市值回看历史。
- [ ] 时间候选区间为 `2020–2024`、`2025`、`2026 YTD` 和 `最新`；缺失区间显示 `incomplete`。
- [ ] “策略探索”是信息架构名称，不代表生产策略、预期收益或晋升结论。
- [ ] 英文只保留 ticker、ETF、FX、USD、schema、数据源和必要技术名；主标题、导航、状态、控件和解释使用中文。

## Target Information Architecture

```text
研究总览
├── 现金流策略探索
├── 小微盘策略探索
│   ├── A股小微盘
│   └── 跨市场小微盘流动性
├── 市场长期风格研究
│   ├── 指数与 ETF
│   ├── Barra / 18 年因子证据
│   └── 长期风格与市场阶段
└── 跨市场探索
    ├── 跨市场流动性
    ├── Global Six-Market
    └── 市场分散与 FX
```

跨市场小微盘流动性研究的观察单位是“市场 × 市值分位 × 时间区间”，不是 Global Six-Market 的固定权重 ETF 组合。

ETF 作为指数/市场代理和长期表现比较属于“市场长期风格研究”；ETF 的交易容量和流动性属于“跨市场探索”；ETF 选品、信号和策略组合属于 `quant-research`。

## Data and Output Contract

统一输入字段至少包括：`market`, `symbol`, `date`, `turnover`, `market_cap`, `currency`, `is_tradable`, `is_suspended`, `source`。

统一派生字段包括：

- `size_bucket`: 当日横截面市值百分位，至少支持 `<20%`、`20–40%`、`40–60%`、`60–80%`、`>=80%`；
- `adv20`: 只使用前 20 个可用观察日的成交额；
- `median_usd`, `mean_usd`, `p90_usd`: 区间内的 bucket-level 流动性统计；
- `period`, `coverage_start`, `coverage_end`, `status`, `observations`；
- `native_currency`, `fx_method`, `universe_filter`, `calendar_mode`, `source_snapshot`。

比较必须明确：A 股、港股、日股、美股的 universe、停牌、成交额单位、市值字段、汇率和 survivor bias 不完全相同；统一 schema 不等于经济含义完全相同。

## File Map

- Modify: `src/market_research/reports.py` — period snapshots and aligned small-cap metrics.
- Modify: `src/market_research/cli.py` — historical report generation and input diagnostics.
- Modify: `src/market_research/quality.py` — readable-input and coverage diagnostics.
- Create: `tests/test_liquidity_periods.py` — period, lag, bucket, and common-intersection tests.
- Modify: `tests/test_reports.py`, `tests/test_cli.py` — compatibility and command tests.
- Modify: `web/scripts/build-public-snapshot.mjs` — derived snapshot filtering.
- Modify/Create: `web/public/data/liquidity/summary.json`, `web/public/data/liquidity/periods.json`.
- Modify: `web/src/main.tsx` — four domains, microcap subtabs, period selector, Chinese copy.
- Modify: `web/src/styles.css` — navigation, overview cards, status badges, responsive layout.
- Modify: `web/src/data.test.mjs`, `web/src/dashboard.test.mjs`, `web/src/editorialUi.test.mjs`.
- Create: `docs/cross-market-smallcap-alignment.md`.
- Create: `docs/research-information-architecture.md`.
- Modify: `README.md`, `docs/runbook-local.md`.

## Task 1: Stabilize the historical liquidity calculation

**Interfaces:**

```python
LIQUIDITY_PERIODS: dict[str, tuple[str, str]]
build_liquidity_periods(
    panels: dict[str, pd.DataFrame],
    periods: dict[str, tuple[str, str]] | None = None,
) -> list[dict[str, object]]
```

- [ ] Keep and refactor the existing uncommitted period prototype in the current worktree.
- [ ] Add fixtures for overlapping HK/A-share/JP ranges, missing markets, fewer than 20 observations, ties, and invalid rows.
- [ ] Test that `ADV20` uses a strict 20-observation lag and never same-day turnover.
- [ ] Test deterministic percentile buckets with one, few, and many securities.
- [ ] Test common coverage dates and `verified`/`incomplete` status.
- [ ] Ensure date handling works for `datetime`, `Timestamp`, and `date` values.
- [ ] Include period diagnostics in `build_liquidity_report` while preserving latest-summary compatibility.
- [ ] Run `uv run pytest tests/test_liquidity_periods.py tests/test_reports.py -q` and then the full suite.
- [ ] Commit `feat: add comparable smallcap liquidity periods`.

## Task 2: Refresh real data from hard-disk assets

- [ ] Inspect the HK cold-data layout and identify daily bars, valuation/market-cap fields, instrument status, currency, and any FX source.
- [ ] Inspect Japanese NIRA daily files and map `Date`, `Code`, `C`, `Vo`, `Va` and master/listing fields into the unified panel.
- [ ] Confirm A-share and US source coverage without copying their files.
- [ ] Diagnose the known malformed A-share Parquet file and repair/quarantine it only through the owning external data asset process.
- [ ] Add preflight errors naming source family and exact unreadable path; never silently skip a corrupt file.
- [ ] Run the report with `as_of` unset and record actual coverage for each market.
- [ ] Confirm whether `2020–2024`, `2025`, and `2026 YTD` are complete common intersections; publish only real derived values.
- [ ] Record source hashes, coverage, units, FX assumptions and market-specific exclusions in metadata.
- [ ] Store no raw file paths in public snapshots.

## Task 3: Align A-share and cross-market small-cap definitions

- [ ] Use the same date-wise size bucket labels and `ADV20` definition across markets.
- [ ] Keep native currency in the provenance record and convert comparison metrics to USD using the configured market-specific FX method.
- [ ] Exclude non-tradable, suspended, non-positive market-cap and invalid turnover rows consistently; report exclusion counts.
- [ ] Preserve market-specific notes for HK cold data and Japanese NIRA rather than pretending their fields are identical to Tushare.
- [ ] Add `definition` metadata with bucket method, liquidity metric, lag, currency, FX method, universe filter and calendar mode.
- [ ] Add tests proving two currencies produce the same schema but different FX metadata.
- [ ] Write `docs/cross-market-smallcap-alignment.md` distinguishing descriptive liquidity evidence from strategy capacity.
- [ ] Commit `docs: define cross-market smallcap alignment`.

## Task 4: Publish historical snapshots

- [ ] Extend the snapshot builder to consume `liquidity_report.json` and emit `periods.json`.
- [ ] Keep `latest` as the default period so existing links and page behavior remain valid.
- [ ] Validate public JSON contains no data roots, credentials, raw file names or absolute paths.
- [ ] Add tests for complete and incomplete periods, including a market missing from one period.
- [ ] Generate snapshots from the real HK cold data and Japanese NIRA run after Task 2.
- [ ] Commit `feat: publish period-aware liquidity snapshots`.

## Task 5: Implement four-domain navigation and microcap subtabs

**State model:**

```typescript
type Domain = "overview" | "cashflow" | "microcap" | "style" | "cross-market";
type MicrocapScope = "a-share" | "cross-market";
type LiquidityPeriod = "latest" | "2020-2024" | "2025" | "2026 YTD";
```

- [ ] Top navigation becomes `研究总览 | 现金流策略探索 | 小微盘策略探索 | 市场长期风格研究 | 跨市场探索`.
- [ ] `小微盘策略探索` contains `A股小微盘 | 跨市场小微盘流动性` subtabs.
- [ ] The cross-market subtab consumes period-aware liquidity snapshots and never duplicates raw-data logic.
- [ ] Add a style-research page grouping existing index/ETF and Barra/18-year market-evidence outputs; alpha/strategy decisions remain in `quant-research`.
- [ ] `跨市场探索` remains the broad home for liquidity, Global Six-Market, FX and diversification studies.
- [ ] Preserve old hash links `#microcap`, `#indices`, `#cashflow`, `#liquidity` where possible, with compatibility tests.
- [ ] Add tests for every top-level route and both microcap subtabs.
- [ ] Commit `feat: organize research domains and microcap subtabs`.

## Task 6: Redesign overview and navigation UI

- [ ] Replace the flat overview with five editorial cards: 现金流策略、小微盘策略、市场长期风格、跨市场探索、研究方法与数据边界.
- [ ] Make the small-cap card visibly point to the two subtabs.
- [ ] Add a compact status strip: `4 个研究域`, `原始数据外置`, `证据优先`, `持续探索`.
- [ ] Fix navigation CSS to target actual `.site-nav a`, including active, hover, keyboard focus and mobile overflow.
- [ ] Use restrained theme accents: cashflow green, microcap terracotta, cross-market blue/ochre, methodology neutral.
- [ ] Keep `a-share-zoo-garden`-inspired typography, whitespace, fine borders and editorial hierarchy without copying project-specific assets.
- [ ] Add status badges for `verified`, `derived`, `incomplete`, and `探索中`.
- [ ] Add failing UI tests for cards, nav labels, focus-visible styling and subtab labels before implementation.
- [ ] Run `npm test`, `npm run build`, and inspect at 320px, 768px and desktop widths.
- [ ] Commit `feat: refine research portal information hierarchy`.

## Task 7: Remove unnecessary English from the public UI

- [ ] Inventory visible strings with `rg` and classify project/technical names versus decorative copy.
- [ ] Translate `Index Research`, `Liquidity Profiles`, `Research Notes`, `Static Snapshot`, and similar decorative labels.
- [ ] Use Chinese primary title for `Global Six-Market`, retaining the English only as a secondary technical label.
- [ ] Translate loading, error, control, table and status strings.
- [ ] Keep ticker symbols, `ETF`, `FX`, `USD`, schema names and source names where they improve precision.
- [ ] Add tests asserting approved Chinese navigation and card labels.
- [ ] Commit `docs: localize research portal copy` or combine with Task 6 when the diff remains reviewable.

## Task 8: Verify, PR, merge and clean up

- [ ] Run full Python tests in the implementation worktree.
- [ ] Run web tests and production build.
- [ ] Run path/secret/large-file scans.
- [ ] Verify real period intersections and do not claim unavailable periods.
- [ ] Create separate PRs for Python/report contract, snapshot/UI, and docs when review boundaries differ.
- [ ] Request review, merge each PR into `main`, update local main, and verify deployed build.
- [ ] Remove merged remote/local branches and worktrees only after merge confirmation.
- [ ] Leave external data assets untouched except through their owning data pipeline.

## Known data gate

The first historical refresh encountered a malformed A-share Parquet asset. The
HK cold data and Japanese NIRA data are explicitly in scope for the next run,
but a period cannot be marked `verified` until all configured market inputs are
readable and the common-coverage report succeeds.
