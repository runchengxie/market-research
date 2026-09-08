import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./main.tsx", import.meta.url), "utf8");
const charts = readFileSync(new URL("./components/MicrocapCharts.tsx", import.meta.url), "utf8");

test("微盘页面保留旧版研究阅读顺序和图表组件", () => {
  assert.match(source, /MicrocapCharts/);
  assert.match(source, /2026 年至今/);
  assert.match(source, /年度收益/);
  assert.match(source, /滚动 CAGR/);
  assert.match(source, /最长水下区间/);
  assert.match(source, /研究解读/);
  assert.match(charts, /dataZoom/);
  assert.match(charts, /AnnualChart/);
  assert.match(charts, /UnderwaterChart/);
});

test("研究总览使用四个研究域和小微盘子主题", () => {
  assert.match(source, /现金流策略探索/);
  assert.match(source, /小微盘策略探索/);
  assert.match(source, /市场长期风格研究/);
  assert.match(source, /跨市场探索/);
  assert.match(source, /跨市场小微盘流动性/);
  assert.match(source, /navItems/);
});
