import { lazy, StrictMode, Suspense, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const NavChart = lazy(() => import("./components/MicrocapCharts").then((module) => ({ default: module.NavChart })));
const AnnualChart = lazy(() => import("./components/MicrocapCharts").then((module) => ({ default: module.AnnualChart })));
const MetricChart = lazy(() => import("./components/MicrocapCharts").then((module) => ({ default: module.MetricChart })));
const UnderwaterChart = lazy(() => import("./components/MicrocapCharts").then((module) => ({ default: module.UnderwaterChart })));
const ResearchBarChart = lazy(() => import("./components/ResearchCharts").then((module) => ({ default: module.ResearchBarChart })));
const ResearchLineChart = lazy(() => import("./components/ResearchCharts").then((module) => ({ default: module.ResearchLineChart })));

type Row = Record<string, string>;
type MicrocapSummary = { metrics: { ytd_2026_as_of?: string; ytd_2026_reference?: string }; caveats?: string[] };
type Tab = "overview" | "microcap" | "style" | "cashflow" | "cross-market" | "indices" | "liquidity";
type MicrocapScope = "a-share" | "cross-market";
type StyleScope = "indices" | "barra";
type Series = { name: string; values: number[]; color: string };
type LiquidityBucket = { label: string; count?: number; median_usd: number; mean_usd: number; p90_usd?: number; observations?: number };
type LiquidityPeriodMarket = { market: string; status: string; as_of?: string; coverage_start?: string; coverage_end?: string; sub_100m_count?: number; sub_100m_median_usd?: number; buckets: LiquidityBucket[] };
type LiquidityPeriod = { period: string; status: string; common_start?: string | null; common_end?: string | null; markets: LiquidityPeriodMarket[] };
type LiquiditySummary = { method: { roll_days: number; metric: string; currency: string; source_project: string }; markets: LiquidityPeriodMarket[]; periods?: LiquidityPeriod[]; caveats: string[] };
type BarraSummary = { source?: { coverage_start?: string; coverage_end?: string }; size_monotonicity?: { quantiles?: number; tail_spread?: number; monotonicity_score?: number; formation_dates?: number }; legacy_barra_result?: { factor_count?: number } };
type HistoricalFactor = { factor: string; days: number; years: number; cumulative_ret: number; geometric_annual_ret: number; annual_vol: number; sharpe: number; max_drawdown: number; hit_rate: number };
type CorrelationMatrix = Record<string, Record<string, number>>;
type DiagnosticView = "daily" | "monthly" | "stage";
type CashflowBasis = "all" | "price_return" | "gross_total_return";

const DATA = "./data";
const pct = (value: number | null | undefined) => value == null || Number.isNaN(value) ? "—" : `${(value * 100).toFixed(1)}%`;
const num = (value: number | string | null | undefined) => value == null || value === "" || Number.isNaN(Number(value)) ? "—" : new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(Number(value));
const asNumber = (value: string | undefined) => value == null || value === "" ? NaN : Number(value);
const displayLabels: Record<string, string> = {
  quarterly: "季度调仓",
  semiannual: "半年调仓",
  price_return: "价格回报",
  gross_total_return: "毛全收益",
  last_week: "近一周",
  last_month: "近一个月",
  last_3_months: "近三个月",
  last_6_months: "近六个月",
  ytd: "年初至今",
  rolling_1_year: "近一年",
  year_2025: "2025 年全年",
  since_20240924: "自 2024 年 9 月 24 日以来",
  last_3_years: "近三年",
  last_5_years: "近五年",
  last_10_years: "近十年",
  last_15_years: "近十五年",
};
const displayValue = (key: string, value: string) => displayLabels[value] ?? value;

function average(values: number[]) { return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : NaN; }
function stageForDate(date: string) {
  const year = Number(date.slice(0, 4));
  return year <= 2019 ? "2015–2019" : year <= 2024 ? "2020–2024" : "2025–当前";
}
function aggregateSizeRows(rows: Row[], period: "month" | "stage") {
  const groups = new Map<string, number[]>();
  rows.forEach((row) => {
    const value = Number(row.forward_return);
    if (!Number.isFinite(value)) return;
    const key = `${period === "month" ? row.formation_date.slice(0, 7) : stageForDate(row.formation_date)}|${row.bucket}`;
    groups.set(key, [...(groups.get(key) ?? []), value]);
  });
  return [...groups.entries()].map(([key, values]) => {
    const [periodLabel, bucket] = key.split("|");
    return { period: periodLabel, bucket, value: average(values) };
  });
}
function summarizeSizePeriods(rows: Row[], period: "month" | "stage") {
  const grouped = aggregateSizeRows(rows, period);
  const periods = [...new Set(grouped.map((row) => row.period))];
  return periods.map((periodLabel) => {
    const values = grouped.filter((row) => row.period === periodLabel);
    const q1 = values.find((row) => row.bucket === "Q1")?.value ?? NaN;
    const q10 = values.find((row) => row.bucket === "Q10")?.value ?? NaN;
    return { period: periodLabel, q1, q10, spread: q1 - q10, observations: values.length };
  });
}

function SizeDiagnosticPanel({ rows, dailyCurve }: { rows: Row[]; dailyCurve: Row[] }) {
  const [view, setView] = useState<DiagnosticView>("monthly");
  const monthly = aggregateSizeRows(rows, "month");
  const monthlyCurve = [...new Set(monthly.map((row) => row.bucket))].map((bucket) => ({ bucket, value: String(average(monthly.filter((row) => row.bucket === bucket).map((row) => row.value))) }));
  const stages = summarizeSizePeriods(rows, "stage");
  const chartRows = view === "daily" ? dailyCurve : view === "monthly" ? monthlyCurve : stages.map((row) => ({ bucket: row.period, value: String(row.spread) }));
  const formatter = (value: number) => `${(value * 100).toFixed(2)}%`;
  return <><Panel title="补充：当前市值分位诊断" tag="当前窗口 · 描述性诊断"><p className="panel-note">这部分根据当前 A 股日频清洗面板重新计算，覆盖 {rows[0]?.formation_date ?? "—"} 至 {rows.at(-1)?.formation_date ?? "—"}。日频结果用来观察排序方向，月频和阶段结果用来检查方向是否稳定。三种口径都属于历史描述。</p><BarChart rows={dailyCurve} labelKey="bucket" valueKey="value" color="#b64d33" formatter={formatter}/><p className="panel-note">上图展示形成日分组后的下一交易日平均收益。日频波动较大，形成日数量不能直接视为独立样本数。</p><SortableTable rows={rows} columns={[["formation_date", "形成日"], ["bucket", "市值分位"], ["forward_return", "未来收益"], ["count", "股票数"]]} percentColumns={["forward_return"]}/></Panel><Panel title="稳定性观察：月频与阶段" tag="减少日频噪音"><p className="panel-note">月频结果先计算每月平均值，再让每个月占相同权重。阶段图展示 Q1 减 Q10 的平均差异。结果属于描述性统计，尚未计算 HAC 标准误、区块自助法置信区间或正式显著性。</p><ControlBar><span className="control-label">观察口径</span><Choice active={view === "daily"} onClick={() => setView("daily")}>日频分位</Choice><Choice active={view === "monthly"} onClick={() => setView("monthly")}>月频分位</Choice><Choice active={view === "stage"} onClick={() => setView("stage")}>阶段尾差</Choice></ControlBar>{view === "stage" ? <><BarChart rows={chartRows} labelKey="bucket" valueKey="value" color="#1267d6" formatter={formatter}/><SimpleTable rows={stages.map((row) => ({ period: row.period, q1: formatter(row.q1), q10: formatter(row.q10), spread: formatter(row.spread), observations: String(row.observations) }))} columns={[["period", "阶段"], ["q1", "Q1平均"], ["q10", "Q10平均"], ["spread", "Q1−Q10"], ["observations", "分位数"]]} /></> : <BarChart rows={chartRows} labelKey="bucket" valueKey="value" color="#1267d6" formatter={formatter}/>}</Panel></>;
}

function parseCsv(text: string): Row[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (char === '"' && text[index + 1] === '"' && quoted) { cell += '"'; index += 1; continue; }
    if (char === '"') { quoted = !quoted; continue; }
    if (char === "," && !quoted) { row.push(cell); cell = ""; continue; }
    if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[index + 1] === "\n") index += 1;
      row.push(cell); cell = "";
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      continue;
    }
    cell += char;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const headers = rows.shift() ?? [];
  return rows.map((values) => Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])));
}

function useJson<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { let active = true; fetch(`${DATA}/${path}`).then((response) => { if (!response.ok) throw new Error(`${path}（${response.status}）`); return response.json() as Promise<T>; }).then((value) => { if (active) setData(value); }).catch((reason: Error) => { if (active) setError(reason.message); }); return () => { active = false; }; }, [path]);
  return { data, error };
}

function useCsv(path: string) {
  const [data, setData] = useState<Row[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { let active = true; fetch(`${DATA}/${path}`).then((response) => { if (!response.ok) throw new Error(`${path}（${response.status}）`); return response.text(); }).then((text) => { if (active) setData(parseCsv(text)); }).catch((reason: Error) => { if (active) setError(reason.message); }); return () => { active = false; }; }, [path]);
  return { data, error };
}

function Stat({ label, value, note, accent = false }: { label: string; value: string; note: string; accent?: boolean }) { return <article className={`stat ${accent ? "accent" : ""}`}><span>{label}</span><strong>{value}</strong><small>{note}</small></article>; }
function Panel({ title, tag, children }: { title: string; tag?: string; children: React.ReactNode }) { return <section className="panel"><div className="panel-title"><h3>{title}</h3>{tag && <span className="tag warm">{tag}</span>}</div>{children}</section>; }
function SectionHeading({ title, text }: { title: string; text: string }) { return <div className="section-heading"><h3>{title}</h3><p>{text}</p></div>; }
function ResearchCard({ title, text }: { title: string; text: string }) { return <article className="research-card"><span className="section-kicker">阅读提示</span><h3>{title}</h3><p>{text}</p></article>; }

function LineChart({ series, labels }: { series: Series[]; labels: string[] }) { return <ResearchLineChart series={series} labels={labels}/>; }
function BarChart({ rows, labelKey, valueKey, color = "#c84b2f", formatter = pct, logScale = false }: { rows: Row[]; labelKey: string; valueKey: string; color?: string; formatter?: (value: number) => string; logScale?: boolean }) { return <ResearchBarChart rows={rows} labelKey={labelKey} valueKey={valueKey} color={color} formatter={formatter} logScale={logScale}/>; }

function ControlBar({ children }: { children: React.ReactNode }) { return <div className="control-bar">{children}</div>; }
function Choice({ active, children, onClick }: { active: boolean; children: React.ReactNode; onClick: () => void }) { return <button className={`choice ${active ? "active" : ""}`} onClick={onClick}>{children}</button>; }
function MicrocapSubTabs({ scope, onChange }: { scope: MicrocapScope; onChange: (value: MicrocapScope) => void }) { return <div className="sub-tabs" aria-label="小微盘研究子主题"><button className={scope === "a-share" ? "active" : ""} onClick={() => onChange("a-share")}>A股小微盘</button><button className={scope === "cross-market" ? "active" : ""} onClick={() => onChange("cross-market")}>跨市场小微盘流动性</button></div>; }
function StyleSubTabs({ scope, onChange }: { scope: StyleScope; onChange: (value: StyleScope) => void }) { return <div className="sub-tabs" aria-label="市场长期风格研究子主题"><button className={scope === "indices" ? "active" : ""} onClick={() => onChange("indices")}>指数与 ETF</button><button className={scope === "barra" ? "active" : ""} onClick={() => onChange("barra")}>Barra · 18年因子研究</button></div>; }

function MicrocapPage({ scope, onScopeChange }: { scope: MicrocapScope; onScopeChange: (value: MicrocapScope) => void }) {
  return <><MicrocapSubTabs scope={scope} onChange={onScopeChange}/>{scope === "cross-market" ? <LiquidityPage embedded/> : <MicrocapPageContent/>}</>;
}

function MicrocapPageContent() {
  const { data: summary } = useJson<MicrocapSummary>("index/microcap/summary.json");
  const { data: reconstructed } = useJson<Row>("index/microcap/reconstructed_summary.json");
  const { data: nav } = useCsv("index/microcap/nav.csv");
  const { data: reconstructedNav } = useCsv("index/microcap/reconstructed_daily_nav.csv");
  const { data: annual } = useCsv("index/microcap/annual_returns.csv");
  const { data: cagr } = useCsv("index/microcap/rolling_cagr.csv");
  const { data: drawdown } = useCsv("index/microcap/rolling_drawdown.csv");
  const { data: underwater } = useCsv("index/microcap/reconstructed_underwater_periods.csv");
  if (!summary || !reconstructed || !nav || !reconstructedNav || !annual || !cagr || !drawdown || !underwater) return <Loading />;
  const latestAnnual = annual.find((row) => row.year === "2025");
  return <><ThemeHeading kicker="历史研究档案 · 微盘规则复现" title="把长期路径、回撤过程和执行难度放在一张图里。" text="审计提示：旧版自制净值存在已选持仓缺报价后重新归一化的问题，尚未完成重算。以下保留为历史档案，不可作为收益或可交易性验证。" asof={`重建截至 ${reconstructedNav.at(-1)?.date ?? "—"}`}/><section className="stat-grid"><Stat label="公开参考净值" value={num(asNumber(nav.at(-1)?.nav))} note={`截至 ${nav.at(-1)?.date ?? "—"}`} accent/><Stat label="2025年收益" value={pct(asNumber(latestAnnual?.return))} note="公开资料参考"/><Stat label="重建最大回撤" value={pct(asNumber(reconstructed.max_drawdown))} note="2015年以来日频"/><Stat label="最长水下时间" value={`${num(asNumber(reconstructed.longest_underwater_trading_days))} 个交易日`} note={`${reconstructed.longest_underwater_start ?? "—"} 至 ${reconstructed.longest_underwater_end ?? "—"}`}/><Stat label="重建样本" value={`${num(asNumber(reconstructed.observations))} 天`} note={`${reconstructed.coverage_start ?? "—"} 至 ${reconstructed.coverage_end ?? "—"}`}/></section><div className="panel ytd-panel"><div className="panel-title"><h3>2026 年至今</h3><span className="tag warm">公开资料参考</span></div><p>截至 {summary.metrics.ytd_2026_as_of ?? "—"}，公开资料参考收益为 <strong>{pct(asNumber(summary.metrics.ytd_2026_reference))}</strong>。规则重建净值更新到 {reconstructed.coverage_end ?? "—"}，两条序列适合分开观察。</p></div><SectionHeading title="收益路径" text="先看长期曲线，再看每日重建净值里的回撤和恢复过程。"/><div className="panel"><div className="panel-title"><h3>公开资料参考净值</h3><span className="tag">可悬停、缩放</span></div><NavChart rows={nav} name="公开资料参考" color="#1267d6"/></div><div className="panel"><div className="panel-title"><h3>连续净值：Tushare 规则重建</h3><span className="tag warm">2015年以来 · 可悬停、缩放</span></div><p className="panel-note">按上海、深圳 A 股总市值选取最小 400 只，等权持有至下一交易日。这里用于观察规则路径，暂未扣除交易成本。</p><NavChart rows={reconstructedNav} name="Tushare 规则重建净值" color="#b96800"/></div><div className="panel"><div className="panel-title"><h3>年度收益</h3><span className="tag warm">悬停查看数值</span></div><AnnualChart rows={annual}/></div><div className="research-grid"><Panel title="滚动年化收益" tag="持有期限"><MetricChart rows={cagr} value="cagr" label="年化收益"/></Panel><Panel title="滚动最大回撤" tag="月频与日频参考"><MetricChart rows={drawdown} value="max_drawdown" label="最大回撤"/></Panel></div><div className="panel"><div className="panel-title"><h3>最长水下区间</h3><span className="tag warm">按交易日排序</span></div><p className="panel-note">水下时间指净值低于此前高点的连续交易日数量。图表展示持续时间最长的 10 个区间，悬停可以查看区间回撤。</p><UnderwaterChart rows={underwater}/></div><SectionHeading title="研究解读" text="规则、收益来源、历史阶段和复制难度沿着同一条阅读路径展开。"/><div className="research-grid"><ResearchCard title="两个微盘口径" text="8841431.WI 每日调仓，适合观察极小市值与再平衡机制。868008.WI 每月调仓，换手和执行压力相对更低。"/><ResearchCard title="收益来源" text="主要暴露包括极小市值、等权再平衡、短期反转和流动性风险溢价。这里是研究解释，不代表精确的因子归因。"/><ResearchCard title="历史阶段" text="2001 至 2005 年连续下跌。2006 至 2015 年多个极端上涨年份抬高长期年化收益。2017 至 2018 年处于风格逆风期。"/><ResearchCard title="复制难度" text="复制能力需要单独验证，不能由指数收益推断。成交不足、涨跌停、停牌、退市和冲击成本都可能造成差异。"/></div><div className="fine-print"><span className="section-kicker">研究边界</span><p>{reconstructed.caveats ?? "这是历史规则重建，与 Wind 官方指数口径不同，也没有计入交易成本、涨跌停和停牌执行限制。"}</p></div></>;
}
function StylePage({ scope, onScopeChange }: { scope: StyleScope; onScopeChange: (value: StyleScope) => void }) {
  return <><StyleSubTabs scope={scope} onChange={onScopeChange}/>{scope === "barra" ? <BarraPage/> : <IndicesPage/>}</>;
}

function IndicesPage() {
  const { data: returns } = useCsv("index/linked_indices/ten_year_price_returns.csv");
  const { data: etfs } = useCsv("index/linked_indices/paired_index_etf_representatives.csv");
  const { data: catalog } = useCsv("index/index_catalog.csv");
  if (!returns || !etfs || !catalog) return <Loading />;
  const top = [...returns].sort((a, b) => asNumber(b.cagr) - asNumber(a.cagr)).slice(0, 12);
  const liquid = etfs.filter((row) => row.liquid_10m === "True").length;
  return <><ThemeHeading kicker="指数长期回报 · ETF 可投资性" title="从指数表现到真实产品，把长期回报和可投资性放在一起。" text="整理指数研究资料中的指数目录、十年价格回报和 ETF 代表配对结果。价格指数不含分红，ETF 数据还会受到费用和跟踪误差影响。" asof="静态公开快照"/><section className="stat-grid"><Stat label="指数目录" value={num(catalog.length)} note="已收录公开目录" accent/><Stat label="十年可比指数" value={num(returns.length)} note="有完整起止数据"/><Stat label="ETF代表" value={num(etfs.length)} note="指数配对结果"/><Stat label="流动性通过" value={num(liquid)} note="近60日成交额筛选"/></section><Panel title="十年价格回报最高的指数" tag="前12名"><BarChart rows={top} labelKey="indx_name" valueKey="cagr" color="#1267d6"/></Panel><Panel title="ETF代表：指数与产品的差异" tag="可搜索、可排序"><SortableTable rows={etfs} columns={[["ts_code", "ETF"], ["matched_index_name", "跟踪指数"], ["etf_cagr", "ETF年化"], ["index_cagr", "指数年化"], ["etf_max_drawdown", "ETF回撤"], ["median_amount_60d", "60日中位成交额"]]} percentColumns={["etf_cagr", "index_cagr", "etf_max_drawdown"]}/></Panel></>;
}

function BarraDiagnosticPage() {
  const { data: summary, error: summaryError } = useJson<BarraSummary>("barra/barra_summary.json");
  const { data: quantiles, error: quantilesError } = useCsv("barra/barra_size_quantiles.csv");
  if (!summary || !quantiles) return <><ThemeHeading kicker="Barra · 18年因子市场证据" title="把长期风格现象放在可复核的分位收益曲线上。" text="这里展示因子摘要和市值尾部的排序诊断，帮助阅读市场长期表现。" asof="快照待发布"/><div className="callout status-panel"><span className="section-kicker">研究状态</span><h3>Barra 快照尚未发布到网页</h3><p>{summaryError || quantilesError ? "网页目录暂时缺少 barra_summary.json 和 barra_size_quantiles.csv。生成报告后即可接入结果。" : "正在加载 Barra 研究快照。"}</p></div></>;
  const monotonicity = summary.size_monotonicity;
  const factorCount = summary.legacy_barra_result?.factor_count;
  const rows = quantiles.map((row) => ({ bucket: row.bucket_label || row.bucket, forward_return: row.mean_forward_return, count: row.count, formation_date: row.formation_date }));
  const curve = Object.values(rows.reduce<Record<string, Row>>((result, row) => { const current = result[row.bucket] ?? { bucket: row.bucket, forward_return: "0", count: "0" }; current.forward_return = String(Number(current.forward_return) + Number(row.forward_return || 0)); current.count = String(Number(current.count) + 1); result[row.bucket] = current; return result; }, {})).map((row) => ({ bucket: row.bucket, value: String(Number(row.forward_return) / Math.max(Number(row.count), 1)) }));
  return <><ThemeHeading kicker="历史研究档案 · Barra 风格因子" title="把长期风格现象放在可复核的历史分位曲线上。" text="这里汇总历史结果包与当前 A 股可复现窗口的市值诊断，帮助阅读市场长期表现。" asof={summary.source ? `当前重算 ${summary.source.coverage_start ?? "—"} 至 ${summary.source.coverage_end ?? "—"}` : "研究快照"}/><section className="stat-grid"><Stat label="历史因子数" value={num(factorCount)} note="来自历史结果包" accent/><Stat label="市值分位" value={num(monotonicity?.quantiles)} note="当前诊断"/><Stat label="尾部价差" value={pct(Number(monotonicity?.tail_spread))} note="Q1 减 Q10"/><Stat label="形成日数量" value={num(monotonicity?.formation_dates)} note="存在时间相关性"/></section><Panel title="市值分位的平均未来收益" tag="历史诊断 · 形成日分位 · 下一交易日收益"><BarChart rows={curve} labelKey="bucket" valueKey="value" color="#b64d33"/></Panel><Panel title="市值分位诊断明细" tag="可搜索、可排序"><SortableTable rows={rows} columns={[["formation_date", "形成日"], ["bucket", "市值分位"], ["forward_return", "未来收益"], ["count", "股票数"]]} percentColumns={["forward_return"]}/></Panel><div className="fine-print"><span className="section-kicker">研究边界</span><p>18 年指历史研究窗口，起止时间为 {summary.source?.coverage_start ?? "—"} 至 {summary.source?.coverage_end ?? "—"}。日频横截面观测存在时间相关性，页面用于描述历史表现，不提供正式显著性检验或交易结论。</p></div></>;
}

const FACTOR_NAMES: Record<string, string> = { beta: "低贝塔", chip_concentration: "筹码集中度", dividend_yield: "股息率", earnings_yield: "盈利收益率", fund_breadth: "公募重仓广度", fund_breadth_change: "公募重仓广度变化", fund_ownership: "公募重仓比例", fund_ownership_change: "公募重仓比例变化", growth: "成长", institution_holding: "机构持仓", leverage: "低杠杆", liquidity: "低换手", liquidity_flow: "大单资金流", lowvol: "低波动", momentum: "21日动量", ps_value: "市销率价值", quality: "质量", size: "市值", value: "价值" };
const FACTOR_DEFINITIONS: Row[] = [
  { factor: "size", name: "市值", direction: "大市值减小市值", method: "总市值自然对数，月度分层" },
  { factor: "value", name: "价值", direction: "低市净率减高市净率", method: "市净率倒数，月度分层" },
  { factor: "momentum", name: "21日动量", direction: "强势减弱势", method: "21日收益，月度分层" },
  { factor: "quality", name: "质量", direction: "高质量减低质量", method: "ROE、低杠杆、盈利稳定性和现金流质量等权合成" },
  { factor: "earnings_yield", name: "盈利收益率", direction: "低市盈率减高市盈率", method: "滚动市盈率倒数" },
  { factor: "lowvol", name: "低波动", direction: "低波动减高波动", method: "最近21个收益观察值的波动率" },
  { factor: "growth", name: "成长", direction: "高增长减低增长", method: "净利润同比和营业收入同比，按公告日对齐" },
  { factor: "leverage", name: "低杠杆", direction: "低杠杆减高杠杆", method: "资产负债率，按公告日对齐" },
  { factor: "beta", name: "低贝塔", direction: "低贝塔减高贝塔", method: "252日滚动市场贝塔，至少126日" },
  { factor: "liquidity", name: "低换手", direction: "低换手减高换手", method: "换手率" },
  { factor: "liquidity_flow", name: "大单资金流", direction: "大单净买入较高减较低", method: "大单净买入占比" },
  { factor: "chip_concentration", name: "筹码集中度", direction: "集中度较高减较低", method: "前十大流通股东持股占比" },
  { factor: "institution_holding", name: "机构持仓", direction: "机构持仓较高减较低", method: "前十大机构流通持股占比" },
  { factor: "fund_breadth", name: "公募前十大重仓广度", direction: "重仓基金较多减较少", method: "月末可见 PIT 状态下的前十大重仓基金数量" },
  { factor: "fund_breadth_change", name: "公募重仓广度变化", direction: "重仓覆盖增加减减少", method: "前十大重仓基金数量相对上期变化" },
  { factor: "fund_ownership", name: "公募重仓比例", direction: "重仓比例较高减较低", method: "前十大重仓流通股持仓比例合计" },
  { factor: "fund_ownership_change", name: "公募重仓比例变化", direction: "重仓比例增加减减少", method: "前十大重仓流通股持仓比例相对上期变化" },
  { factor: "dividend_yield", name: "股息率", direction: "高股息率减低股息率", method: "过去12个月股息率" },
  { factor: "ps_value", name: "市销率价值", direction: "低市销率减高市销率", method: "滚动市销率倒数" },
];

function BarraPage() {
  const { data: summary, error: summaryError } = useJson<BarraSummary>("barra/barra_summary.json");
  const { data: quantiles, error: quantilesError } = useCsv("barra/barra_size_quantiles.csv");
  const { data: factors } = useJson<HistoricalFactor[]>("barra/historical_factor_summary.json");
  const { data: yearly } = useCsv("barra/factor_yearly.csv");
  const { data: correlations } = useJson<CorrelationMatrix>("barra/factor_correlation.json");
  const [selectedFactor, setSelectedFactor] = useState("size");
  if (!summary || !quantiles || !factors || !yearly || !correlations) return <><ThemeHeading kicker="历史研究档案 · Barra 风格因子" title="把长期风格现象还原成一份可阅读的历史研究。" text="这里介绍历史结果包的方法、因子表现、逐年收益和相关性，市值分位诊断放在最后作为补充。" asof="历史快照加载中"/><div className="callout status-panel"><span className="section-kicker">研究状态</span><h3>历史研究快照正在加载</h3><p>{summaryError || quantilesError ? "网页数据不完整，请先生成并发布 Barra 历史派生文件。" : "正在加载历史因子总览、逐年收益和相关性数据。"}</p></div></>;
  const monotonicity = summary.size_monotonicity;
  const quantileRows = quantiles.map((row) => ({ bucket: row.bucket_label || row.bucket, forward_return: row.mean_forward_return, count: row.count, formation_date: row.formation_date }));
  const quantileCurve = Object.values(quantileRows.reduce<Record<string, Row>>((result, row) => { const current = result[row.bucket] ?? { bucket: row.bucket, forward_return: "0", count: "0" }; current.forward_return = String(Number(current.forward_return) + Number(row.forward_return || 0)); current.count = String(Number(current.count) + 1); result[row.bucket] = current; return result; }, {})).map((row) => ({ bucket: row.bucket, value: String(Number(row.forward_return) / Math.max(Number(row.count), 1)) }));
  const factorRows = factors.map((factor) => ({ factor: FACTOR_NAMES[factor.factor] ?? factor.factor, coverage: `${factor.years} 年 · ${factor.days} 日`, annual: String(factor.geometric_annual_ret / 100), vol: String(factor.annual_vol / 100), sharpe: String(factor.sharpe), drawdown: String(factor.max_drawdown / 100), hit: String(factor.hit_rate / 100) }));
  const selectedYearly = yearly.filter((row) => row.factor === selectedFactor).map((row) => ({ year: row.year, value: String(asNumber(row.annual_ret) / 100) }));
  const related = Object.entries(correlations[selectedFactor] ?? {}).filter(([factor]) => factor !== selectedFactor).sort(([, left], [, right]) => Math.abs(right) - Math.abs(left)).slice(0, 8).map(([factor, value]) => ({ factor: FACTOR_NAMES[factor] ?? factor, correlation: String(value) }));
  const selectedFactorSummary = factors.find((factor) => factor.factor === selectedFactor);
  return <><ThemeHeading kicker="历史研究档案 · Barra 风格因子" title="把长期风格现象还原成一份可阅读的历史研究。" text="页面完整呈现历史结果包中的研究问题、因子定义、长期表现、逐年收益、相关性和数据覆盖，市值分位诊断放在最后作为补充。" asof="历史样本 2008-01-02 至 2026-09-04"/><div className="callout research-status"><span className="section-kicker">研究性质</span><h3>历史描述性证据 · 多空合成收益，供回顾市场表现</h3><p>这里的年化和逐年收益由因子高分组减低分组的日收益差复合而来，是历史多空合成收益，不代表可实现的策略账户回报。Barra 风格风险分析也可用于风险暴露解释和归因，不等同于预测性 alpha；本页是分组价差研究。</p></div><SectionHeading title="研究问题与方法" text="先说明研究对象，再阅读数字，避免把历史结果误读成未来预测。"/><div className="research-grid"><ResearchCard title="研究对象" text="研究 19 个 A 股横截面风格因子，按历史数据构造的形成日得分分为五组。最高 20% 与最低 20% 两端月末等权建仓，固定份额持有至下个月末，日收益按高分组减低分组合成；财务数据的完整 PIT 可见性尚未验证。"/><ResearchCard title="行业处理" text="因子先按历史生效区间匹配的申万一级行业去均值，再进行全市场标准化。缺少行业匹配的股票归入残差组；信号去均值不保证多空组合行业权重中性。"/><ResearchCard title="样本口径" text="大部分基础因子覆盖约 18.6 年。机构持仓、筹码和公募持仓类因子覆盖约 11 年或更短，资金流因子约 0.6 年。"/></div><div className="callout"><span className="section-kicker">信号证据与执行边界</span><p>判断排序信号时，IC、rankIC（形成日得分与未来收益的横截面相关性）及分位收益单调性是更直接的证据，仍需样本外和统计检验。本页未提供 IC / rankIC 结果；下方市值十分位是独立重算诊断，不是历史五分位多空收益的复核。</p><p>历史多空序列未验证逐期融券券源、借券成本和保证金约束，也未纳入完整交易成本与执行限制，不能据此推定 A 股组合可执行或一概不可执行。</p></div><Panel title="因子定义与方向" tag="历史研究方法"><SimpleTable rows={FACTOR_DEFINITIONS} columns={[["name", "因子"], ["direction", "方向"], ["method", "构造方法"]]} /></Panel><Panel title="19 个因子表现总览" tag="历史多空合成收益 · 非策略账户回报"><SortableTable rows={factorRows} columns={[["factor", "因子"], ["coverage", "覆盖"], ["annual", "多空合成几何年化"], ["vol", "年化波动"], ["sharpe", "Sharpe"], ["drawdown", "最大回撤"], ["hit", "日胜率"]]} percentColumns={["annual", "vol", "drawdown", "hit"]}/></Panel><Panel title="逐年收益与阶段观察 · 多空合成" tag="日收益差的年度复合 · 非策略账户回报"><ControlBar><span className="control-label">因子</span>{factors.map((factor) => <Choice key={factor.factor} active={selectedFactor === factor.factor} onClick={() => setSelectedFactor(factor.factor)}>{FACTOR_NAMES[factor.factor] ?? factor.factor}</Choice>)}</ControlBar><BarChart rows={selectedYearly} labelKey="year" valueKey="value" color="#1267d6"/><p className="panel-note">{FACTOR_NAMES[selectedFactor] ?? selectedFactor}：覆盖 {selectedFactorSummary?.years ?? "—"} 年，多空合成几何年化 {pct((selectedFactorSummary?.geometric_annual_ret ?? 0) / 100)}，数值沿用历史结果包；年度值仅覆盖该年已有观察日，未完整年度不作全年外推。</p></Panel><Panel title="因子相关性" tag="历史多空日收益差的相关性"><SimpleTable rows={related} columns={[["factor", "因子"], ["correlation", "相关系数"]]} /></Panel><SizeDiagnosticPanel rows={quantileRows} dailyCurve={quantileCurve}/><div className="fine-print"><span className="section-kicker">研究限制</span><p>历史报告使用基础日行情、日频估值和后续重建的历史财务数据，并非完整 PIT（当时实际可见版本）数据；按公告日对齐也不能证明历史修订已被排除。不同因子的覆盖期不同，横向比较时需要留意样本长度差异。日频收益存在时间相关性，Sharpe、年化、回撤和胜率均描述合成序列，未进行正式显著性检验、自助法分析或多重检验校正。历史计算将持仓期缺失收益记为零，未完整处理退市终值；手续费、容量、涨跌停、停牌和实际执行约束仍需另行复核。</p></div></>;
}

function CashflowPage() {
  const { data: rows } = useCsv("index/cashflow_indices/cashflow_performance.csv");
  const { data: frequency } = useCsv("index/cashflow_indices/cashflow_rebalance_frequency.csv");
  const [windowKey, setWindowKey] = useState("rolling_1_year");
  const [basis, setBasis] = useState<CashflowBasis>("all");
  if (!rows || !frequency) return <Loading />;
  const codes = [...new Set(rows.map((row) => row.ts_code))];
  const windows = [...new Set(rows.map((row) => row.window))].sort((left, right) => (Object.keys(displayLabels).indexOf(left) + 100) - (Object.keys(displayLabels).indexOf(right) + 100));
  const matching = rows.filter((row) => row.window === windowKey && (basis === "all" || row.return_basis === basis));
  const comparison = basis === "all" ? matching : codes.map((code) => matching.find((row) => row.ts_code === code) ?? { ts_code: code, name: rows.find((row) => row.ts_code === code)?.name ?? code, window: windowKey, return_basis: basis, return: "", cagr: "" });
  const windowLabel = displayLabels[windowKey] ?? windowKey;
  const basisLabel = basis === "all" ? "全部回报口径" : displayLabels[basis];
  const asOf = [...new Set(rows.map((row) => row.as_of).filter(Boolean))].sort().at(-1);
  return <><ThemeHeading kicker="现金流指数 · 股息与调仓研究" title="比较现金流指数在不同周期下的历史表现。" text="页面提供时间窗口、回报口径和调仓频率筛选，方便对照价格回报与毛全收益。" asof={`数据截至 ${asOf ?? "—"}`}/><section className="stat-grid"><Stat label="指数样本" value={num(codes.length)} note="现金流指数家族" accent/><Stat label="主要调仓" value={displayValue("rebalance_frequency", frequency[0]?.rebalance_frequency ?? "—")} note="方法论频率"/><Stat label="表现观察窗" value={num(windows.length)} note="从近一周到近十年"/></section><Panel title="指数收益对比" tag={`${windowLabel} · ${basisLabel}`}><ControlBar><span className="control-label">时间窗口</span>{windows.map((value) => <Choice key={value} active={windowKey === value} onClick={() => setWindowKey(value)}>{displayValue("window", value)}</Choice>)}<span className="control-label">回报口径</span>{[["all", "全部口径"], ["price_return", "价格回报"], ["gross_total_return", "毛全收益"]].map(([value, label]) => <Choice key={value} active={basis === value} onClick={() => setBasis(value as CashflowBasis)}>{label}</Choice>)}</ControlBar>{comparison.length ? <BarChart rows={comparison} labelKey="name" valueKey="return" color="#1267d6"/> : <p className="panel-note">当前窗口没有对应回报口径的数据。</p>}</Panel><Panel title="当前窗口的表现明细"><SortableTable rows={comparison} columns={[["name", "指数"], ["rebalance_frequency", "调仓"], ["return_basis", "回报口径"], ["window", "窗口"], ["return", "累计回报"], ["cagr", "年化"]]} percentColumns={["return", "cagr"]}/></Panel></>;
}

function AnimalPage() {
  const { data: animalLatest } = useJson<Row>("animal/latest.json");
  const { data: animalHistory } = useJson<Row[]>("animal/history.json");
  const { data: animalChanges } = useJson<Row>("animal/changes.json");
  const { data: plantLatest } = useJson<Row>("plant/latest.json");
  const { data: plantHistory } = useJson<Row[]>("plant/history.json");
  const { data: animalConstituents } = useJson<Row[]>("animal/constituents.json");
  const { data: plantConstituents } = useJson<Row[]>("plant/constituents.json");
  if (!animalLatest || !animalHistory || !animalChanges || !plantLatest || !plantHistory || !animalConstituents || !plantConstituents) return <Loading />;
  return <><ThemeHeading kicker="A股动物 / 植物指数 · 规则化观察" title="把主题规则、净值路径和调仓变化放在一起。" text="整理动物与植物指数资料中的两套指数快照，包括严格/扩展口径、基准、历史净值、当前成分和调仓变化。" asof={`截至 ${animalLatest.date}`}/><section className="stat-grid"><Stat label="动物严格口径" value={num(animalLatest.zoo_strict_nav)} note={pct(asNumber(animalLatest.zoo_strict_daily))} accent/><Stat label="动物扩展口径" value={num(animalLatest.zoo_extended_nav)} note={pct(asNumber(animalLatest.zoo_extended_daily))}/><Stat label="植物严格口径" value={num(plantLatest.zoo_strict_nav)} note={pct(asNumber(plantLatest.zoo_strict_daily))}/><Stat label="沪深300 ETF" value={num(animalLatest.benchmark_nav)} note={pct(asNumber(animalLatest.benchmark_daily))}/></section><Panel title="主题指数净值路径" tag="月度调仓"><LineChart labels={animalHistory.map((row) => row.date)} series={[{ name: "动物严格", values: animalHistory.map((row) => Number(row.zoo_strict_nav)), color: "#c84b2f" }, { name: "动物扩展", values: animalHistory.map((row) => Number(row.zoo_extended_nav)), color: "#1267d6" }, { name: "植物严格", values: plantHistory.map((row) => Number(row.zoo_strict_nav)), color: "#51855f" }]}/></Panel><div className="research-grid"><Panel title="当前动物成分"><SimpleTable rows={animalConstituents.slice(0, 12)} columns={Object.keys(animalConstituents[0] ?? {}).slice(0, 4).map((key) => [key, key])}/></Panel><Panel title="当前植物成分"><SimpleTable rows={plantConstituents.slice(0, 12)} columns={Object.keys(plantConstituents[0] ?? {}).slice(0, 4).map((key) => [key, key])}/></Panel><Panel title="最近调仓变化"><SimpleTable rows={Object.entries(animalChanges).map(([variant, value]) => ({ variant, detail: JSON.stringify(value) }))} columns={[["variant", "口径"], ["detail", "变化"]]}/></Panel></div></>;
}

function LiquidityPage({ embedded = false }: { embedded?: boolean }) { return <><LiquidityPeriodPanel embedded={embedded}/><LiquidityPageLegacy/></>; }

function LiquidityPeriodPanel({ embedded }: { embedded: boolean }) {
  const { data: summary } = useJson<LiquiditySummary>("liquidity/summary.json");
  const [period, setPeriod] = useState("latest");
  if (!summary) return <Loading />;
  const options = ["latest", ...(summary.periods ?? []).map((item) => item.period)];
  const selected = period === "latest" ? null : summary.periods?.find((item) => item.period === period);
  const markets = selected?.markets ?? summary.markets;
  const available = markets.filter((item) => item.status !== "incomplete");
  const periodStatus = selected?.status ?? "mixed";
  const latestDates = markets.filter((item) => item.as_of).map((item) => `${item.market} ${item.as_of}`).join("，");
  const statusLabel = periodStatus === "verified" ? "口径已核验" : periodStatus === "mixed" ? "日期不一致" : periodStatus === "pending" ? "待生成" : "覆盖不完整";
  return <section className={`period-panel ${embedded ? "embedded" : ""}`}><div className="period-heading"><div><span className="section-kicker">跨市场小微盘流动性</span><h3>按各市场最近可用数据比较小市值股票的流动性</h3><p>每个市场按自身最近可用数据分桶，使用滞后 20 日平均成交额。由于数据更新不同步，页面单独列出各市场的数据日期。</p></div><span className={`status-badge ${periodStatus}`}>{statusLabel}</span></div><ControlBar><span className="control-label">时间区间</span>{options.map((value) => { const item = value === "latest" ? null : summary.periods?.find((candidate) => candidate.period === value); const itemStatus = item?.status; return <Choice key={value} active={period === value} onClick={() => setPeriod(value)}>{value === "latest" ? "最近可用快照" : value}{itemStatus === "incomplete" ? " · 覆盖不完整" : itemStatus === "pending" ? " · 待生成" : ""}</Choice>; })}</ControlBar><div className="period-meta">{selected ? `${selected.common_start ?? "—"} 至 ${selected.common_end ?? "—"} · ${available.length}/${markets.length} 个市场可比` : `各市场最近可用快照 · ${latestDates || "日期待补充"}`}</div>{selected && selected.status === "incomplete" && <div className="callout compact"><span className="section-kicker">覆盖提醒</span><p>该区间的市场覆盖范围不完全一致，下面只展示有数据的市场，缺失市场不会填成零。</p></div>}{selected && selected.status === "pending" && <div className="callout compact"><span className="section-kicker">生成状态</span><p>该区间的数据预计可以计算，当前网页还没有发布分桶汇总。生成后会补充共同覆盖日期和市场明细。</p></div>}<div className="period-table">{available.length ? <SimpleTable rows={available.flatMap((market) => market.buckets.map((bucket) => ({ market: `${market.market}（截至 ${selected ? market.coverage_end ?? "日期待补" : market.as_of ?? "日期待补"}）`, bucket: bucket.label, median_usd: `$${num(bucket.median_usd)}`, mean_usd: `$${num(bucket.mean_usd)}`, observations: num(bucket.observations) })))} columns={[["market", "市场"], ["bucket", "市值分位"], ["median_usd", "成交中位"], ["mean_usd", "成交均值"], ["observations", "观测数"]]} /> : <p className="panel-note">当前时间段还没有可展示的分桶汇总。</p>}</div></section>;
}

function LiquidityPageLegacy() {
  const { data: summary } = useJson<LiquiditySummary>("liquidity/summary.json");
  const [market, setMarket] = useState("all");
  const [metric, setMetric] = useState<"median_usd" | "mean_usd" | "p90_usd">("median_usd");
  const [logScale, setLogScale] = useState(true);
  if (!summary) return <Loading />;
  const markets = summary.markets.filter((item) => market === "all" || item.market === market);
  const comparison = markets.map((item) => ({ market: item.market, value: String(item.buckets[0]?.[metric] ?? item.sub_100m_median_usd) }));
  const bucketRows = markets.flatMap((item) => item.buckets.map((bucket) => ({ market: item.market, bucket: bucket.label, count: String(bucket.count), median_usd: String(bucket.median_usd), mean_usd: String(bucket.mean_usd), p90_usd: bucket.p90_usd == null ? "—" : String(bucket.p90_usd) })));
  const metricLabel = metric === "median_usd" ? "成交中位" : metric === "mean_usd" ? "成交均值" : "P90";
  return <><ThemeHeading kicker="小微盘历史研究 · 跨市场流动性" title="流动性需要同时看成交规模、市场结构和数据覆盖。" text="这里汇总不同市场小市值尾部的流动性差异。原始行情不公开，页面展示脱敏汇总和数据状态。" asof={`${summary.method.roll_days}日平均 · ${summary.method.currency}`}/><ControlBar><span className="control-label">市场</span><Choice active={market === "all"} onClick={() => setMarket("all")}>全部</Choice>{summary.markets.map((item) => <Choice key={item.market} active={market === item.market} onClick={() => setMarket(item.market)}>{item.market}</Choice>)}<span className="control-label">指标</span><Choice active={metric === "median_usd"} onClick={() => setMetric("median_usd")}>中位数</Choice><Choice active={metric === "mean_usd"} onClick={() => setMetric("mean_usd")}>均值</Choice><Choice active={metric === "p90_usd"} onClick={() => setMetric("p90_usd")}>P90</Choice><Choice active={logScale} onClick={() => setLogScale(!logScale)}>{logScale ? "对数坐标" : "线性坐标"}</Choice></ControlBar><section className="stat-grid">{markets.map((item, index) => <Stat key={item.market} label={`${item.market} · <$100m`} value={`$${num(item.sub_100m_median_usd)}`} note={`${num(item.sub_100m_count)} 只股票`} accent={index === markets.length - 1}/>)}</section><Panel title="小市值股票的流动性中位数" tag={`${metricLabel} · ${logScale ? "对数" : "线性"}`}><BarChart rows={comparison} labelKey="market" valueKey="value" color="#1267d6" formatter={(value) => `$${num(value)}`} logScale={logScale}/></Panel><Panel title="跨市场市值分桶明细" tag="美元成交额"><SimpleTable rows={bucketRows} columns={[["market", "市场"], ["bucket", "市值区间"], ["count", "数量"], ["median_usd", "成交中位"], ["mean_usd", "成交均值"], ["p90_usd", "P90"]]} /></Panel><div className="fine-print"><span className="section-kicker">数据与研究边界</span><p>{summary.caveats.join(" ")}</p></div><div className="research-grid"><article className="research-card"><span className="section-kicker">定义</span><h3>成交额不能直接代表容量</h3><p>页面将名义成交、滞后 ADV、MedADV、参与率和冲击成本拆开，帮助判断实际可执行规模。</p></article><article className="research-card"><span className="section-kicker">时间</span><h3>特征严格滞后一天</h3><p>流动性特征不使用当日成交额，避免把当天结果带入交易前的可投资性判断。</p></article><article className="research-card"><span className="section-kicker">数据边界</span><h3>日股仍待补充同口径快照</h3><p>日股数据适配器已经接入统一 Python 接口，日股分桶结果还要等本地数据完成同口径刷新。</p></article></div></>;
}

function ThemeHeading({ kicker, title, text, asof }: { kicker: string; title: string; text: string; asof: string }) { return <header className="theme-heading"><div><span className="section-kicker">{kicker}</span><h2>{title}</h2><p>{text}</p></div><span className="asof">{asof}</span></header>; }
function SimpleTable({ rows, columns, percentColumns = [] }: { rows: Row[]; columns: string[][]; percentColumns?: string[] }) { return <div className="table-scroll"><table><thead><tr>{columns.map(([key, label]) => <th key={key}>{label}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={`${index}-${row[columns[0]?.[0] ?? ""]}`}>{columns.map(([key]) => <td key={key}>{percentColumns.includes(key) ? pct(asNumber(row[key])) : row[key] === "" || row[key] == null ? "—" : displayValue(key, row[key])}</td>)}</tr>)}</tbody></table></div>; }
function SortableTable({ rows, columns, percentColumns = [], searchPlaceholder = "搜索表格内容" }: { rows: Row[]; columns: string[][]; percentColumns?: string[]; searchPlaceholder?: string }) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState(columns[0]?.[0] ?? "");
  const [direction, setDirection] = useState<"asc" | "desc">("desc");
  const visible = rows.filter((row) => Object.values(row).some((value) => value.toLowerCase().includes(query.toLowerCase()))).sort((left, right) => {
    const a = asNumber(left[sortKey]);
    const b = asNumber(right[sortKey]);
    const comparison = Number.isFinite(a) && Number.isFinite(b) ? a - b : String(left[sortKey] ?? "").localeCompare(String(right[sortKey] ?? ""));
    return direction === "desc" ? -comparison : comparison;
  });
  const choose = (key: string) => { if (key === sortKey) setDirection(direction === "desc" ? "asc" : "desc"); else { setSortKey(key); setDirection("desc"); } };
  return <><div className="table-controls"><input aria-label={searchPlaceholder} placeholder={searchPlaceholder} value={query} onChange={(event) => setQuery(event.target.value)}/><span>{visible.length} / {rows.length} 条</span></div><div className="table-scroll"><table><thead><tr>{columns.map(([key, label]) => <th key={key}><button className="table-sort" onClick={() => choose(key)}>{label} {sortKey === key ? (direction === "desc" ? "↓" : "↑") : "↕"}</button></th>)}</tr></thead><tbody>{visible.slice(0, 50).map((row, index) => <tr key={`${index}-${row[columns[0]?.[0] ?? ""]}`}>{columns.map(([key]) => <td key={key}>{percentColumns.includes(key) ? pct(asNumber(row[key])) : row[key] === "" || row[key] == null ? "—" : displayValue(key, row[key])}</td>)}</tr>)}</tbody></table></div></>;
}
function Loading() { return <p className="loading">正在加载研究快照……</p>; }

function App() {
  const validTabs: Tab[] = ["overview", "microcap", "style", "cashflow", "cross-market", "indices", "liquidity"];
  const hash = window.location.hash.slice(1) as Tab;
  const [tab, setTab] = useState<Tab>(validTabs.includes(hash) ? hash : "overview");
  const [microcapScope, setMicrocapScope] = useState<MicrocapScope>("a-share");
  useEffect(() => { const onHash = () => { const next = window.location.hash.slice(1) as Tab; if (validTabs.includes(next)) setTab(next); }; window.addEventListener("hashchange", onHash); return () => window.removeEventListener("hashchange", onHash); }, []);
  const [styleScope, setStyleScope] = useState<StyleScope>("indices");
  const page = tab === "microcap" || tab === "cross-market" ? <MicrocapPage scope={tab === "cross-market" ? "cross-market" : microcapScope} onScopeChange={setMicrocapScope}/> : tab === "style" ? <StylePage scope={styleScope} onScopeChange={setStyleScope}/> : tab === "indices" ? <IndicesPage/> : tab === "cashflow" ? <CashflowPage/> : tab === "liquidity" ? <LiquidityPage/> : <Overview/>;
  const navItems: [Tab, string][] = [["overview", "档案总览"], ["cashflow", "现金流历史研究"], ["microcap", "小微盘历史研究"], ["style", "长期风格历史研究"]];
  return <div className="app"><header className="site-header"><div className="site-masthead"><div><span className="brand-kicker">历史研究档案 · 证据优先</span><h1>市场研究档案</h1><p className="site-deck">以历史研究为主线，区分已完成证据、进行中专题和待补数据。</p></div><div className="site-meta"><span>历史档案 · 研究中 · 待补数据</span><strong>原始数据外置 · 描述性证据</strong></div></div><nav className="site-nav" aria-label="研究主题">{navItems.map(([key, label]) => <a key={key} className={tab === key || (key === "style" && tab === "indices") || (key === "cross-market" && tab === "liquidity") ? "active" : ""} href={`#${key}`} onClick={() => setTab(key)}>{label}</a>)}</nav></header><main className="site-main">{page}</main><footer className="site-footer"><span>市场研究档案 · 历史证据优先</span><a href="https://github.com/runchengxie/quant-market-research">查看 GitHub 仓库 ↗</a></footer></div>;
}

function Overview() { return <><ThemeHeading kicker="历史研究档案 · 目录" title="先回顾已经形成的证据，再查看正在推进的专题。" text="本项目以历史市场研究为主线，公开可复核的派生快照。研究中的专题和待补数据会单独标注。" asof="公开快照"/><section className="overview-grid"><a href="#cashflow"><span className="section-kicker">01 · 历史研究</span><h3>现金流历史研究</h3><p>回顾现金流、股息和调仓频率在不同回报口径与持有窗口下的表现。</p><b>进入档案 ↗</b></a><a href="#microcap"><span className="section-kicker">02 · 历史研究</span><h3>小微盘历史研究</h3><p>A股小微盘规则重建与跨市场小微盘流动性，分别通过两个子主题阅读。</p><b>进入档案 ↗</b></a><a href="#style"><span className="section-kicker">03 · 历史研究</span><h3>长期风格历史研究</h3><p>指数、ETF、Barra 和 18 年因子研究，放在同一条历史证据线上。</p><b>进入档案 ↗</b></a></section><div className="callout"><span className="section-kicker">研究复核笔记</span><h3><a href="./research/recovery.html">现金流与小微盘研究复核摘要 ↗</a></h3><p>查看独立研究笔记中的复核结论、证据范围与待验证事项。</p></div><section className="research-grid"><ResearchCard title="历史研究优先" text="页面优先呈现已经完成的市场研究文档和可复核快照，研究中的假设会单独标注。"/><ResearchCard title="描述性证据" text="ETF 作为市场代理，指数表现和 18 年因子现象用于描述市场长期特征。它们不能直接说明 alpha 或策略是否应该上线。"/><ResearchCard title="研究状态优先" text="每个专题保留来源、样本区间和限制条件。日频观察数量需要结合时间相关性理解。"/></section><div className="fine-print"><span className="section-kicker">数据与研究边界</span><p>策略研究、历史市场证据和通用平台能力分开维护。原始行情不公开，跨市场比较不会把缺失市场填成零。六市场配置研究等尚未形成完整快照的内容归入待补数据与未来研究。</p></div></>; }

createRoot(document.getElementById("root")!).render(<StrictMode><Suspense fallback={<Loading />}><App /></Suspense></StrictMode>);
