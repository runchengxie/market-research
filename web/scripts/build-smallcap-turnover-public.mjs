import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const outputRoot = process.env.MARKET_RESEARCH_OUTPUT_ROOT ?? "/home/richard/data/market-research/outputs";
const publicPath = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../public/data/smallcap_turnover.json");

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (char === '"' && text[index + 1] === '"' && quoted) { cell += '"'; index += 1; continue; }
    if (char === '"') { quoted = !quoted; continue; }
    if (char === "," && !quoted) { row.push(cell); cell = ""; continue; }
    if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[index + 1] === "\n") index += 1;
      row.push(cell);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      cell = "";
      continue;
    }
    cell += char;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const headers = rows.shift() ?? [];
  return rows.map((values) => Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])));
}

function median(values) {
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function aggregate(rows, period) {
  const groups = new Map();
  rows.forEach((row) => {
    const label = period === "year" ? row.date.slice(0, 4) : row.date.slice(0, 7);
    const key = label + "|" + row.rank_count;
    const group = groups.get(key) ?? { label, rank_count: Number(row.rank_count), median: [], coverage: [], selected: new Set(), dates: new Set() };
    group.median.push(Number(row.turnover_median));
    group.coverage.push(Number(row.coverage_ratio));
    group.selected.add(Number(row.selected_count));
    group.dates.add(row.date);
    groups.set(key, group);
  });
  return [...groups.values()].sort((left, right) => left.label.localeCompare(right.label) || left.rank_count - right.rank_count).map((group) => ({
    [period === "year" ? "year" : "month"]: period === "year" ? Number(group.label) : group.label,
    rank_count: group.rank_count,
    turnover_median: median(group.median),
    trading_days: group.dates.size,
    median_coverage_ratio: median(group.coverage),
    min_selected_count: Math.min(...group.selected),
  }));
}

function buildSnapshot(fileName, qualityStatus) {
  const rows = parseCsv(fs.readFileSync(path.join(outputRoot, fileName), "utf8"));
  return {
    coverage_start: rows[0].date,
    coverage_end: rows.at(-1).date,
    quality_status: qualityStatus,
    rank_counts: [...new Set(rows.map((row) => Number(row.rank_count)))].sort((left, right) => left - right),
    annual: aggregate(rows, "year"),
    monthly: aggregate(rows, "month"),
  };
}

const auditRows = parseCsv(fs.readFileSync(path.join(outputRoot, "smallcap_turnover_overlap_audit.csv"), "utf8"));
const overlapAudit = auditRows.map((row) => Object.fromEntries([
  ["rank_count", Number(row.rank_count)],
  ["common_days", Number(row.common_days)],
  ["common_start", row.common_start],
  ["common_end", row.common_end],
  ["mean_abs_relative_diff_turnover_median", Number(row.mean_abs_relative_diff_turnover_median)],
  ["p90_abs_relative_diff_turnover_median", Number(row.p90_abs_relative_diff_turnover_median)],
  ["within_5pct_ratio", Number(row.within_5pct_ratio)],
  ["within_10pct_ratio", Number(row.within_10pct_ratio)],
  ["within_25pct_ratio", Number(row.within_25pct_ratio)],
  ["quality_note", row.quality_note],
]));

const snapshot = {
  schema_version: "smallcap_turnover_ui.v2",
  method: "按每日总市值选取最小 N 只股票，统计当日成交额分布；年度和月度值为交易日层面指标的聚合。",
  clean: buildSnapshot("smallcap_turnover_daily.csv", "verified"),
  historical: buildSnapshot("smallcap_turnover_history_daily.csv", "incomplete"),
  overlap_audit: overlapAudit,
  caveats: [
    "2015 年起清洗口径覆盖 ST、停牌和价格质量规则，适合做当前主分析。",
    "2008 年起历史口径覆盖更长，但历史源缺少可靠的 ST/停牌标记，标记为 incomplete，不应与清洗口径直接视为同一序列。",
    "N=1 只有每日市值最小的一只股票，受个股异常、停牌、涨跌停和资格切换影响很大，仅作为极端诊断，不代表可交易组合。",
    "网页发布年度和月度汇总及审计摘要；完整日频明细保留在仓库外的研究输出目录。",
  ],
};

fs.writeFileSync(publicPath, JSON.stringify(snapshot, null, 2) + "\n");
console.log("Wrote " + publicPath);
