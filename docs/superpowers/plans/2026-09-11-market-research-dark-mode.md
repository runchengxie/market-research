# Quant Market Research Dark Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `quant-market-research` 增加可持久化的浅色/深色/系统主题切换，并保证研究页面和 ECharts 在两种主题下可读。

**Architecture:** 新增小型 `theme.ts` 纯函数/浏览器适配模块管理主题选择和解析；`main.tsx` 负责启动时应用 `data-theme`、监听系统变化和渲染切换控件；`styles.css` 与图表组件通过 CSS variables 共享颜色。数据加载、hash 路由和研究组件保持不变。

**Tech Stack:** React/TypeScript、CSS variables、ECharts、Node built-in test、Vite。

**Spec:** `docs/superpowers/specs/2026-09-11-market-research-dark-mode-design.md`

## Global Constraints

- 暖白 editorial 主题继续作为默认主题。
- `light / dark / system` 选择保存在 `localStorage` key `market-research-theme`。
- 不修改研究数据、页面信息架构、URL、Python 或发布快照。
- 不引入第三方主题依赖。
- 暗色图表必须保持 chart surface、页面背景、axis/grid、tooltip 的可区分性。

---

### Task 1: Add theme utility and failing contracts

**Files:**
- Create: `web/src/theme.ts`
- Create: `web/src/theme.test.mjs`
- Modify: `web/src/editorialUi.test.mjs` only if test fixture organization requires it

**Interfaces:** `theme.ts` exports `ThemeChoice`, `resolveTheme(choice, prefersDark)`, `readThemeChoice(storage)`, `persistThemeChoice(storage, choice)`, and `applyTheme(choice, prefersDark, documentElement)`.

- [ ] **Step 1: Write failing tests** for default light resolution, explicit dark/light resolution, malformed localStorage fallback to `system`, persistence of valid choices, and `applyTheme` setting `data-theme`.
- [ ] **Step 2: Run `npm test` from `web/` and confirm only the new theme tests fail because `theme.ts` does not exist.**
- [ ] **Step 3: Implement the minimal pure utility and browser adapters with no React dependency.**
- [ ] **Step 4: Run `npm test` from `web/` and confirm the theme tests pass.**

### Task 2: Add theme state and dark visual tokens

**Files:**
- Modify: `web/src/main.tsx`
- Modify: `web/index.html`
- Modify: `web/src/styles.css`
- Modify: `web/src/components/MicrocapCharts.tsx`
- Modify: `web/src/components/ResearchCharts.tsx`
- Create: `web/src/themeUi.test.mjs`

**Interfaces:** `App` uses the Task 1 theme utility; chart components keep existing props and read shared chart colors through a helper or CSS variables.

- [ ] **Step 1: Add a pre-paint inline script in `web/index.html` that reads `market-research-theme`, resolves system preference, and sets `document.documentElement.dataset.theme`.**
- [ ] **Step 2: Add `useState`/`useEffect` theme handling in `main.tsx`, render a button in `.site-meta`, and update the theme on click without changing tab/hash state.**
- [ ] **Step 3: Replace core hard-coded layout colors in `styles.css` with variables while preserving current light values. Add `[data-theme="dark"]` values for paper, surfaces, text, muted text, rules, accent, callouts, table hover, and tooltip.**
- [ ] **Step 4: Add chart color helpers using CSS variables so axis, grid, label and tooltip colors update after theme changes; keep supplied business series colors and data unchanged.**
- [ ] **Step 5: Write source-level UI contracts for the theme button, pre-paint script, dark variables, and chart variable usage; run `npm test` and expect all tests to pass.**

### Task 3: Verify production build and accessibility boundaries

**Files:**
- Modify: only files needed to correct a verified regression

- [ ] **Step 1: Run `npm run build` from `web/` and confirm Vite/TypeScript succeeds.**
- [ ] **Step 2: Run `git diff --check` and inspect that no public data or generated snapshot changed.**
- [ ] **Step 3: Confirm theme control has an accessible label, visible focus state, and does not hide existing navigation on mobile.**
- [ ] **Step 4: Commit with `git add web/src web/index.html docs/superpowers/specs/2026-09-11-market-research-dark-mode-design.md docs/superpowers/plans/2026-09-11-market-research-dark-mode.md && git commit -m "feat: add dark mode to market research archive"`.**
