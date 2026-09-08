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
  assert.match(source, /现金流历史研究/);
  assert.match(source, /小微盘历史研究/);
  assert.match(source, /长期风格历史研究/);
  assert.match(source, /研究中的专题/);
  assert.match(source, /历史研究档案/);
  assert.match(source, /描述性市场证据/);
  assert.match(source, /跨市场小微盘流动性/);
  assert.match(source, /Barra · 18年因子研究/);
  assert.match(source, /Barra 快照尚未发布到网页/);
  assert.match(source, /navItems/);
});
