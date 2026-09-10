# Featured Style Factor Study Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the existing 18-year A-share style-factor study the public research flagship without duplicating its implementation or overstating unverified evidence.

**Architecture:** Keep `quant-market-research` as the research archive and keep the existing Barra-derived snapshots as the data source. Add a presentation-level featured-study card and a stable `#style-factors-18y` route that opens the existing Barra view directly; sharpen the page narrative and explicitly distinguish the canonical four factor families from the historical 19-factor descriptive snapshot.

**Tech Stack:** React 18, TypeScript, Vite, Node test runner, YAML study configuration.

**Spec:** User-requested implementation of the previously discussed Quant Research portfolio recommendations.

## Global Constraints

- Do not copy vendor raw data, credentials, private alpha, or unreviewed research outputs into this repository.
- Do not present IC, OOS, statistical significance, or uncertainty estimates as available until corresponding artifacts exist.
- Preserve the existing archive routes and existing evidence-boundary language.
- Keep reusable factor computation in the existing research projects; this change is presentation and study metadata only.

---

### Task 1: Lock the featured-study and direct-route behavior with tests

**Files:**
- Modify: `web/src/overview.test.mjs`
- Modify: `web/src/editorialUi.test.mjs`
- Modify: `web/src/main.tsx`

**Interfaces:**
- `ResearchOverview` renders a featured study link with stable hash `#style-factors-18y`.
- `App` accepts `#style-factors-18y`, selects the style tab, and selects the Barra scope.

- [ ] **Step 1: Write the failing tests**

Add assertions that the overview contains the featured-study title, the direct hash, a research-question sentence, and that the source includes route handling which maps `style-factors-18y` to the `style` tab and `barra` scope.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `cd web && npm test -- overview.test.mjs editorialUi.test.mjs`

Expected: FAIL because the featured card and route mapping do not exist yet.

- [ ] **Step 3: Implement the minimal behavior**

Add the featured study to `ResearchOverview`; add `style-factors-18y` to the route type/valid route handling; set `styleScope` to `barra` when the initial hash or hashchange uses the direct route; preserve `#style` as the archive entry point.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `cd web && npm test -- overview.test.mjs editorialUi.test.mjs`

Expected: PASS with zero failures.

- [ ] **Step 5: Commit**

```bash
git add web/src/overview.test.mjs web/src/editorialUi.test.mjs web/src/main.tsx web/src/components/ResearchOverview.tsx
git commit -m "feat: feature the 18-year style factor study"
```

### Task 2: Sharpen the study narrative and metadata

**Files:**
- Modify: `web/src/main.tsx`
- Modify: `studies/style_factors_18y/study.yml`
- Modify: `studies/style_factors_18y/README.md`
- Modify: `web/src/editorialUi.test.mjs`

**Interfaces:**
- The Barra page title, subtitle, and callouts describe an empirical study of style-factor dynamics and regime dependence.
- The page continues to label the output as historical synthetic long-short evidence and keeps current limitations visible.
- `study.yml` exposes `core_factor_families` separately from the 19-factor historical archive.

- [ ] **Step 1: Write the failing tests**

Add source assertions for the research-question copy, the “Barra-like/style-factor” boundary, and the explicit `core_factor_families` metadata.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `cd web && npm test -- editorialUi.test.mjs`

Expected: FAIL because the current page uses archive-first copy and the new metadata is absent.

- [ ] **Step 3: Implement the minimal narrative changes**

Change the Barra page heading to “18 年 A 股风格因子动态：收益、稳定性与市场阶段”, add the explicit research question, call the output Barra-like/style-factor attribution rather than a full Barra implementation, and state that IC/OOS/statistical evidence remain future work. Update the study README and YAML to say the historical snapshot contains 19 factors while the canonical replication currently focuses on four core families.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `cd web && npm test -- editorialUi.test.mjs`

Expected: PASS with zero failures.

- [ ] **Step 5: Commit**

```bash
git add web/src/main.tsx web/src/editorialUi.test.mjs studies/style_factors_18y/study.yml studies/style_factors_18y/README.md
git commit -m "docs: clarify style factor study scope"
```

### Task 3: Run full verification and inspect the final diff

**Files:**
- No planned new files.

- [ ] **Step 1: Run Python tests**

Run: `uv run --extra duckdb --with pytest pytest -q`

Expected: PASS with zero failures.

- [ ] **Step 2: Run web tests and production build**

Run: `cd web && npm test && npm run build`

Expected: PASS with zero failures and a successful Vite build.

- [ ] **Step 3: Check the diff and repository status**

Run: `git diff --check && git status --short && git diff --stat`

Expected: no whitespace errors; only the planned files are changed.

- [ ] **Step 4: Commit any required test-only correction**

If verification exposes a directly related issue, fix it with a focused test-first change and rerun the affected command before committing. Do not broaden scope to add IC/OOS artifacts.
