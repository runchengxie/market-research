import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./main.tsx", import.meta.url), "utf8");
const charts = readFileSync(new URL("./components/MicrocapCharts.tsx", import.meta.url), "utf8");
const researchCharts = readFileSync(new URL("./components/ResearchCharts.tsx", import.meta.url), "utf8");

test("微盘页面保留旧版研究阅读顺序和图表组件", () => {
  assert.match(source, /MicrocapCharts/);
  assert.match(source, /2026 年至今/);
  assert.match(source, /年度收益/);
  assert.match(source, /滚动年化收益/);
  assert.match(source, /最长未回到前高的区间/);
  assert.match(source, /研究解读/);
  assert.match(charts, /dataZoom/);
  assert.match(charts, /AnnualChart/);
  assert.match(charts, /UnderwaterChart/);
});

test("研究总览使用三个研究域和小微盘子主题", () => {
  assert.match(source, /现金流历史研究/);
  assert.match(source, /小微盘历史研究/);
  assert.match(source, /长期风格历史研究/);
  assert.match(source, /历史研究档案/);
  assert.match(source, /实际账户盈亏/);
  assert.match(source, /跨市场小微盘流动性/);
  assert.match(source, /研究问题与方法/);
  assert.match(source, /19 个因子表现总览/);
  assert.match(source, /逐年合成收益与阶段表现/);
  assert.match(source, /因子相关性/);
  assert.match(source, /历史多空合成收益/);
  assert.match(source, /Barra 风格因子研究（18年）/);
  assert.match(source, /style-factors-18y/);
  assert.match(source, /setStyleScope\("barra"\)/);
  assert.match(source, /ResearchBarChart/);
  assert.match(source, /ResearchLineChart/);
  assert.match(source, /稳定性观察：按月与按阶段/);
  assert.match(source, /区块自助法/);
  assert.match(source, /2015–2019/);
  assert.match(source, /搜索表格内容/);
  assert.match(source, /Barra 快照尚未发布到网页/);
  assert.match(source, /navItems/);
  assert.match(source, /时间窗口/);
  assert.match(source, /各市场最近可用数据/);
  assert.doesNotMatch(source, /跨市场研究中/);
});

test("18年风格研究以经验研究问题呈现并明确Barra边界", () => {
  assert.match(source, /18 年 A 股风格因子动态：收益、稳定性与市场阶段/);
  assert.match(source, /这些风格因子在不同 A 股市场阶段是否持续存在/);
  assert.match(source, /Barra-like/);
  assert.match(source, /IC、样本外验证和统计显著性仍待补充/);
});

test("收益图表为缺失值保留 N/A 标记", () => {
  assert.match(researchCharts, /未提供/);
  assert.match(source, /当前窗口没有对应回报口径的数据/);
});

test("小微盘页面呈现成交额研究的覆盖与审计边界", () => {
  assert.match(source, /小微盘成交额研究/);
  assert.match(source, /2008 年起历史口径/);
  assert.match(source, /重叠审计/);
  assert.match(source, /smallcap_turnover\.json/);
});
