import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import { AnnualChart, MetricChart, NavChart, UnderwaterChart } from "./components/MicrocapCharts";

type Row = Record<string, string>;
type MicrocapSummary = { metrics: { ytd_2026_as_of?: string; ytd_2026_reference?: string }; caveats?: string[] };
type Tab = "overview" | "microcap" | "style" | "cashflow" | "cross-market" | "indices" | "liquidity";
type MicrocapScope = "a-share" | "cross-market";
type StyleScope = "indices" | "barra";
type Series = { name: string; values: number[]; color: string };
type LiquidityBucket = { label: string; count?: number; median_usd: number; mean_usd: number; p90_usd?: number; observations?: number };
type LiquidityPeriodMarket = { market: string; status: string; coverage_start?: string; coverage_end?: string; sub_100m_count?: number; sub_100m_median_usd?: number; buckets: LiquidityBucket[] };
type LiquidityPeriod = { period: string; status: string; common_start?: string | null; common_end?: string | null; markets: LiquidityPeriodMarket[] };
type LiquiditySummary = { method: { roll_days: number; metric: string; currency: string; source_project: string }; markets: LiquidityPeriodMarket[]; periods?: LiquidityPeriod[]; caveats: string[] };
type BarraSummary = { source?: { coverage_start?: string; coverage_end?: string }; size_monotonicity?: { quantiles?: number; tail_spread?: number; monotonicity_score?: number; formation_dates?: number }; legacy_barra_result?: { factor_count?: number } };
type HistoricalFactor = { factor: string; days: number; years: number; cumulative_ret: number; geometric_annual_ret: number; annual_vol: number; sharpe: number; max_drawdown: number; hit_rate: number };
type CorrelationMatrix = Record<string, Record<string, number>>;

const DATA = "./data";
const pct = (value: number | null | undefined) => value == null || Number.isNaN(value) ? "—" : `${(value * 100).toFixed(1)}%`;
const num = (value: number | string | null | undefined) => value == null || value === "" || Number.isNaN(Number(value)) ? "—" : new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(Number(value));
const asNumber = (value: string | undefined) => value == null || value === "" ? NaN : Number(value);

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

function LineChart({ series, labels }: { series: Series[]; labels: string[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const all = series.flatMap((item) => item.values.filter(Number.isFinite));
  const min = Math.min(...all);
  const max = Math.max(...all);
  const spread = max - min || 1;
  const points = (values: number[]) => values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${96 - ((value - min) / spread) * 82}`).join(" ");
  const hoverX = hover == null ? null : (hover / Math.max(labels.length - 1, 1)) * 100;
  return <div className="chart interactive-chart"><svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={series.map((item) => item.name).join("、")} onMouseMove={(event) => { const box = event.currentTarget.getBoundingClientRect(); setHover(Math.max(0, Math.min(labels.length - 1, Math.round(((event.clientX - box.left) / box.width) * Math.max(labels.length - 1, 1))))); }} onMouseLeave={() => setHover(null)}><line x1="0" x2="100" y1="14" y2="14" stroke="#ded6c9"/><line x1="0" x2="100" y1="55" y2="55" stroke="#ded6c9"/><line x1="0" x2="100" y1="96" y2="96" stroke="#ded6c9"/>{series.map((item) => <polyline key={item.name} points={points(item.values)} fill="none" stroke={item.color} strokeWidth="1.2" vectorEffect="non-scaling-stroke"/>)}{hoverX != null && <line x1={hoverX} x2={hoverX} y1="4" y2="98" stroke="#252525" strokeDasharray="2 2" vectorEffect="non-scaling-stroke"/>}</svg>{hover != null && <div className="chart-tooltip" style={{ left: `${Math.min(Math.max(hoverX ?? 0, 12), 88)}%` }}><strong>{labels[hover] ?? "—"}</strong>{series.map((item) => <span key={item.name}><i style={{ background: item.color }}/>{item.name}: {num(item.values[hover])}</span>)}</div>}<div className="chart-axis"><span>{labels[0] ?? "—"}</span><div className="legend">{series.map((item) => <span key={item.name}><i style={{ background: item.color }}/>{item.name}</span>)}</div><span>{labels.at(-1) ?? "—"}</span></div></div>;
}

function BarChart({ rows, labelKey, valueKey, color = "#c84b2f", formatter = pct, logScale = false }: { rows: Row[]; labelKey: string; valueKey: string; color?: string; formatter?: (value: number) => string; logScale?: boolean }) {
  const selected = rows.filter((row) => Number.isFinite(asNumber(row[valueKey]))).slice(-24);
  const values = selected.map((row) => asNumber(row[valueKey]));
  const scale = (value: number) => logScale ? Math.log10(Math.max(Math.abs(value), 1)) : Math.abs(value);
  const max = Math.max(...values.map(scale), 1);
  return <div className="bar-chart">{selected.map((row) => { const value = asNumber(row[valueKey]); const width = Math.min(scale(value) / max * 50, 50); return <div className="bar-row" key={`${row[labelKey]}-${row[valueKey]}`} title={`${row[labelKey]}：${formatter(value)}`}><span title={row[labelKey]}>{row[labelKey]}</span><div className="bar-track diverging"><b className="bar-zero"/><i className={value < 0 ? "negative" : "positive"} style={{ width: `${width}%`, left: value < 0 ? `${50 - width}%` : "50%", background: value < 0 ? "#8e4d48" : color }}/></div><strong>{formatter(value)}</strong></div>; })}</div>;
}

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
  return <><ThemeHeading kicker="历史研究档案 · 微盘规则复现" title="把长期路径、回撤过程和执行难度放在一张图里。" text="页面展示公开资料参考净值，以及基于本地 Tushare 数据复现编制思路的连续净值。它们用于回顾历史路径，不代表未来策略收益。" asof={`重建截至 ${reconstructedNav.at(-1)?.date ?? "—"}`}/><section className="stat-grid"><Stat label="公开参考净值" value={num(asNumber(nav.at(-1)?.nav))} note={`截至 ${nav.at(-1)?.date ?? "—"}`} accent/><Stat label="2025年收益" value={pct(asNumber(latestAnnual?.return))} note="公开资料参考"/><Stat label="重建最大回撤" value={pct(asNumber(reconstructed.max_drawdown))} note="2015年以来日频"/><Stat label="最长水下时间" value={`${num(asNumber(reconstructed.longest_underwater_trading_days))} 个交易日`} note={`${reconstructed.longest_underwater_start ?? "—"} 至 ${reconstructed.longest_underwater_end ?? "—"}`}/><Stat label="重建样本" value={`${num(asNumber(reconstructed.observations))} 天`} note={`${reconstructed.coverage_start ?? "—"} 至 ${reconstructed.coverage_end ?? "—"}`}/></section><div className="panel ytd-panel"><div className="panel-title"><h3>2026 年至今</h3><span className="tag warm">公开资料参考</span></div><p>截至 {summary.metrics.ytd_2026_as_of ?? "—"}，公开资料参考收益为 <strong>{pct(asNumber(summary.metrics.ytd_2026_reference))}</strong>。规则重建净值更新到 {reconstructed.coverage_end ?? "—"}，两条序列适合分开观察。</p></div><SectionHeading title="收益路径" text="先看长期曲线，再看每日重建净值里的回撤和恢复过程。"/><div className="panel"><div className="panel-title"><h3>公开资料参考净值</h3><span className="tag">可悬停、缩放</span></div><NavChart rows={nav} name="公开资料参考" color="#1267d6"/></div><div className="panel"><div className="panel-title"><h3>连续净值：Tushare 规则重建</h3><span className="tag warm">2015年以来 · 可悬停、缩放</span></div><p className="panel-note">按上海、深圳 A 股总市值选取最小 400 只，等权持有至下一交易日。这里用于观察规则路径，暂未扣除交易成本。</p><NavChart rows={reconstructedNav} name="Tushare 规则重建净值" color="#b96800"/></div><div className="panel"><div className="panel-title"><h3>年度收益</h3><span className="tag warm">悬停查看数值</span></div><AnnualChart rows={annual}/></div><div className="research-grid"><Panel title="滚动 CAGR" tag="持有期限"><MetricChart rows={cagr} value="cagr" label="年化收益"/></Panel><Panel title="滚动最大回撤" tag="月频与日频参考"><MetricChart rows={drawdown} value="max_drawdown" label="最大回撤"/></Panel></div><div className="panel"><div className="panel-title"><h3>最长水下区间</h3><span className="tag warm">按交易日排序</span></div><p className="panel-note">水下时间指净值低于此前高点的连续交易日数量。图表展示持续时间最长的 10 个区间，悬停可以查看区间回撤。</p><UnderwaterChart rows={underwater}/></div><SectionHeading title="研究解读" text="规则、收益来源、历史阶段和复制难度沿着同一条阅读路径展开。"/><div className="research-grid"><ResearchCard title="两个微盘口径" text="8841431.WI 每日调仓，适合观察极小市值与再平衡机制。868008.WI 每月调仓，换手和执行压力相对更低。"/><ResearchCard title="收益来源" text="主要暴露包括极小市值、等权再平衡、短期反转和流动性风险溢价。这里是研究解释，不代表精确的因子归因。"/><ResearchCard title="历史阶段" text="2001 至 2005 年连续下跌。2006 至 2015 年多个极端上涨年份抬高长期 CAGR。2017 至 2018 年处于风格逆风期。"/><ResearchCard title="复制难度" text="小资金可以接近完整复制。规模扩大后，需要抽样、优化执行，并承担成交不足、涨跌停、停牌和冲击成本。"/></div><div className="fine-print"><span className="section-kicker">研究边界</span><p>{reconstructed.caveats ?? "这是历史规则重建，与 Wind 官方指数口径不同，也没有计入交易成本、涨跌停和停牌执行限制。"}</p></div></>;
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
  return <><ThemeHeading kicker="指数长期回报 · ETF可投资性" title="从指数表现到真实产品，把长期回报和可投资性放在一起。" text="恢复 index-research 的指数目录、十年价格回报和 ETF 代表配对结果。价格指数不含分红，ETF 数据还会受到费用和跟踪误差影响。" asof="静态公开快照"/><section className="stat-grid"><Stat label="指数目录" value={num(catalog.length)} note="已收录公开目录" accent/><Stat label="十年可比指数" value={num(returns.length)} note="有完整起止数据"/><Stat label="ETF代表" value={num(etfs.length)} note="指数配对结果"/><Stat label="流动性通过" value={num(liquid)} note="近60日成交额筛选"/></section><Panel title="十年价格回报最高的指数" tag="前12名"><BarChart rows={top} labelKey="indx_name" valueKey="cagr" color="#1267d6"/></Panel><Panel title="ETF代表：指数与产品的差异" tag="可搜索、可排序"><SortableTable rows={etfs} columns={[["ts_code", "ETF"], ["matched_index_name", "跟踪指数"], ["etf_cagr", "ETF年化"], ["index_cagr", "指数年化"], ["etf_max_drawdown", "ETF回撤"], ["median_amount_60d", "60日中位成交额"]]} percentColumns={["etf_cagr", "index_cagr", "etf_max_drawdown"]}/></Panel></>;
}

function BarraDiagnosticPage() {
  const { data: summary, error: summaryError } = useJson<BarraSummary>("barra/barra_summary.json");
  const { data: quantiles, error: quantilesError } = useCsv("barra/barra_size_quantiles.csv");
  if (!summary || !quantiles) return <><ThemeHeading kicker="Barra · 18年因子市场证据" title="把长期风格现象放在可复核的分位收益曲线上。" text="这里展示市场证据层的因子摘要与市值尾部单调性诊断，不替代 alpha 选择、IC/衰减分析或策略晋升判断。" asof="快照待发布"/><div className="callout status-panel"><span className="section-kicker">研究状态</span><h3>Barra 快照尚未发布到网页</h3><p>{summaryError || quantilesError ? "当前网页目录还没有可读取的 barra_summary.json 与 barra_size_quantiles.csv。生成报告后即可接入真实结果。" : "正在加载 Barra 研究快照。"}</p></div></>;
  const monotonicity = summary.size_monotonicity;
  const factorCount = summary.legacy_barra_result?.factor_count;
  const rows = quantiles.map((row) => ({ bucket: row.bucket_label || row.bucket, forward_return: row.mean_forward_return, count: row.count, formation_date: row.formation_date }));
  const curve = Object.values(rows.reduce<Record<string, Row>>((result, row) => { const current = result[row.bucket] ?? { bucket: row.bucket, forward_return: "0", count: "0" }; current.forward_return = String(Number(current.forward_return) + Number(row.forward_return || 0)); current.count = String(Number(current.count) + 1); result[row.bucket] = current; return result; }, {})).map((row) => ({ bucket: row.bucket, value: String(Number(row.forward_return) / Math.max(Number(row.count), 1)) }));
  return <><ThemeHeading kicker="历史研究档案 · Barra 风格因子" title="把长期风格现象放在可复核的历史分位曲线上。" text="这里汇总历史结果包与当前 A 股可复现窗口的市值诊断；它是描述性市场证据，不是统计显著性或策略有效性的证明。" asof={summary.source ? `当前重算 ${summary.source.coverage_start ?? "—"} 至 ${summary.source.coverage_end ?? "—"}` : "研究快照"}/><section className="stat-grid"><Stat label="历史因子数" value={num(factorCount)} note="来自历史结果包" accent/><Stat label="市值分位" value={num(monotonicity?.quantiles)} note="当前描述性诊断"/><Stat label="尾部价差" value={pct(Number(monotonicity?.tail_spread))} note="Q1 减 Q10"/><Stat label="形成日数量" value={num(monotonicity?.formation_dates)} note="不是独立样本数"/></section><Panel title="市值分位的平均未来收益" tag="历史诊断 · 形成日分位 · 下一交易日收益"><BarChart rows={curve} labelKey="bucket" valueKey="value" color="#b64d33"/></Panel><Panel title="市值分位诊断明细" tag="可搜索、可排序"><SortableTable rows={rows} columns={[["formation_date", "形成日"], ["bucket", "市值分位"], ["forward_return", "未来收益"], ["count", "股票数"]]} percentColumns={["forward_return"]}/></Panel><div className="fine-print"><span className="section-kicker">研究边界</span><p>“18 年”表示历史研究窗口，不是 2018 年。当前可复现窗口为 {summary.source?.coverage_start ?? "—"} 至 {summary.source?.coverage_end ?? "—"}；日频横截面观测存在时间相关性，这里没有进行正式显著性检验，也不等同于 alpha、IC、衰减或可交易策略收益。</p></div></>;
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
  if (!summary || !quantiles || !factors || !yearly || !correlations) return <><ThemeHeading kicker="历史研究档案 · Barra 风格因子" title="把长期风格现象还原成一份可阅读的历史研究。" text="这里展示历史结果包中的方法、因子表现、逐年收益和相关性；当前市值分位诊断只是补充分析。" asof="历史快照加载中"/><div className="callout status-panel"><span className="section-kicker">研究状态</span><h3>历史研究快照正在加载</h3><p>{summaryError || quantilesError ? "网页数据不完整，请先生成并发布 Barra 历史派生文件。" : "正在加载历史因子总览、逐年收益和相关性数据。"}</p></div></>;
  const monotonicity = summary.size_monotonicity;
  const quantileRows = quantiles.map((row) => ({ bucket: row.bucket_label || row.bucket, forward_return: row.mean_forward_return, count: row.count, formation_date: row.formation_date }));
  const quantileCurve = Object.values(quantileRows.reduce<Record<string, Row>>((result, row) => { const current = result[row.bucket] ?? { bucket: row.bucket, forward_return: "0", count: "0" }; current.forward_return = String(Number(current.forward_return) + Number(row.forward_return || 0)); current.count = String(Number(current.count) + 1); result[row.bucket] = current; return result; }, {})).map((row) => ({ bucket: row.bucket, value: String(Number(row.forward_return) / Math.max(Number(row.count), 1)) }));
  const factorRows = factors.map((factor) => ({ factor: FACTOR_NAMES[factor.factor] ?? factor.factor, coverage: `${factor.years} 年 · ${factor.days} 日`, annual: String(factor.geometric_annual_ret / 100), vol: String(factor.annual_vol / 100), sharpe: String(factor.sharpe), drawdown: String(factor.max_drawdown / 100), hit: String(factor.hit_rate / 100) }));
  const selectedYearly = yearly.filter((row) => row.factor === selectedFactor).map((row) => ({ year: row.year, value: String(asNumber(row.annual_ret) / 100) }));
  const related = Object.entries(correlations[selectedFactor] ?? {}).filter(([factor]) => factor !== selectedFactor).sort(([, left], [, right]) => Math.abs(right) - Math.abs(left)).slice(0, 8).map(([factor, value]) => ({ factor: FACTOR_NAMES[factor] ?? factor, correlation: String(value) }));
  const selectedFactorSummary = factors.find((factor) => factor.factor === selectedFactor);
  return <><ThemeHeading kicker="历史研究档案 · Barra 风格因子" title="把长期风格现象还原成一份可阅读的历史研究。" text="页面完整呈现历史结果包中的研究问题、因子定义、长期表现、逐年收益、相关性与数据覆盖；市值分位是补充分析。" asof="历史样本 2008-01-02 至 2026-09-04"/><div className="callout research-status"><span className="section-kicker">研究性质</span><h3>历史描述性证据，不是策略晋升结论</h3><p>这份研究回答“过去的市场风格现象是什么”，不回答“未来是否还能赚钱”。年化收益、Sharpe 和命中率是样本内描述，没有进行正式显著性检验、Bootstrap 或多重检验校正。</p></div><SectionHeading title="研究问题与方法" text="先说明研究对象，再阅读数字，避免把历史结果误读成未来预测。"/><div className="research-grid"><ResearchCard title="研究对象" text="研究 19 个 A 股横截面风格因子，按形成日可见信息分层，最高 20% 与最低 20% 组合在月末等权建仓并持有至下一个月末。"/><ResearchCard title="行业处理" text="因子先按历史生效区间匹配的申万一级行业去均值，再进行全市场标准化；缺少行业匹配的股票作为残差组处理。"/><ResearchCard title="样本口径" text="大部分基础因子覆盖约 18.6 年；机构持仓、筹码和公募持仓类因子只有约 11 年或更短，资金流因子仅约 0.6 年。"/></div><Panel title="因子定义与方向" tag="历史研究方法"><SimpleTable rows={FACTOR_DEFINITIONS} columns={[["name", "因子"], ["direction", "方向"], ["method", "构造方法"]]} /></Panel><Panel title="19 个因子表现总览" tag="历史样本描述"><SortableTable rows={factorRows} columns={[["factor", "因子"], ["coverage", "覆盖"], ["annual", "几何年化"], ["vol", "年化波动"], ["sharpe", "Sharpe"], ["drawdown", "最大回撤"], ["hit", "日胜率"]]} percentColumns={["annual", "vol", "drawdown", "hit"]}/></Panel><Panel title="逐年收益与阶段观察" tag="选择因子"><ControlBar><span className="control-label">因子</span>{factors.map((factor) => <Choice key={factor.factor} active={selectedFactor === factor.factor} onClick={() => setSelectedFactor(factor.factor)}>{FACTOR_NAMES[factor.factor] ?? factor.factor}</Choice>)}</ControlBar><BarChart rows={selectedYearly} labelKey="year" valueKey="value" color="#1267d6"/><p className="panel-note">{FACTOR_NAMES[selectedFactor] ?? selectedFactor}：覆盖 {selectedFactorSummary?.years ?? "—"} 年，几何年化 {pct((selectedFactorSummary?.geometric_annual_ret ?? 0) / 100)}，仅作为历史样本路径阅读。</p></Panel><Panel title="因子相关性" tag="与当前选择因子的相关性"><SimpleTable rows={related} columns={[["factor", "因子"], ["correlation", "相关系数"]]} /></Panel><Panel title="补充：当前市值分位诊断" tag="不是完整 18 年因子结果"><p className="panel-note">这部分基于当前 canonical A 股 daily-clean 面板重新计算，覆盖 {summary.source?.coverage_start ?? "—"} 至 {summary.source?.coverage_end ?? "—"}。它用于补充观察市值尾部排序，不替代上面的历史 19 因子报告；形成日数量为 {num(monotonicity?.formation_dates)}，不是独立样本数量。</p><BarChart rows={quantileCurve} labelKey="bucket" valueKey="value" color="#b64d33"/><SortableTable rows={quantileRows} columns={[["formation_date", "形成日"], ["bucket", "市值分位"], ["forward_return", "未来收益"], ["count", "股票数"]]} percentColumns={["forward_return"]}/></Panel><div className="fine-print"><span className="section-kicker">研究限制</span><p>历史报告使用基础日行情、日频估值和后续重建的历史财务数据；不同因子覆盖期不同，不能把所有因子横向视为同一长度样本。日频收益存在时间相关性，Sharpe、年化收益和逐年表现不等于统计显著性，也不包含手续费、容量、涨跌停、停牌和实际执行约束。</p></div></>;
}

function CashflowPage() {
  const { data: rows } = useCsv("index/cashflow_indices/cashflow_performance.csv");
  const { data: frequency } = useCsv("index/cashflow_indices/cashflow_rebalance_frequency.csv");
  if (!rows || !frequency) return <Loading />;
  const codes = [...new Set(rows.map((row) => row.ts_code))];
  const oneYear = codes.map((code) => rows.find((row) => row.ts_code === code && row.window === "rolling_1_year") ?? rows.find((row) => row.ts_code === code)).filter((row): row is Row => Boolean(row));
  return <><ThemeHeading kicker="现金流指数 · 股息与调仓研究" title="现金流风格，放在同一套回报和频率口径里比较。" text="恢复现金流指数的多周期表现、回报口径和调仓频率。页面分别展示全收益和价格回报。" asof={`数据截至 ${rows[0]?.as_of ?? "—"}`}/><section className="stat-grid"><Stat label="指数样本" value={num(codes.length)} note="现金流指数家族" accent/><Stat label="主要调仓" value={frequency[0]?.rebalance_frequency ?? "—"} note="方法论频率"/><Stat label="表现观察窗" value={num(new Set(rows.map((row) => row.window)).size)} note="从近一周到十年"/></section><Panel title="滚动一年累计表现" tag="回报口径可见"><BarChart rows={oneYear} labelKey="name" valueKey="return" color="#1267d6"/></Panel><Panel title="完整表现明细"><SimpleTable rows={rows.filter((row) => row.window === "rolling_1_year" || row.window === "year_2025")} columns={[["name", "指数"], ["rebalance_frequency", "调仓"], ["return_basis", "回报口径"], ["window", "窗口"], ["return", "累计回报"], ["cagr", "年化"]]} percentColumns={["return", "cagr"]}/></Panel></>;
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
  return <><ThemeHeading kicker="A股动物 / 植物指数 · 规则化观察" title="把主题规则、净值路径和调仓变化放在一起。" text="恢复 a-share-animal-index 的动物与植物两套指数快照，包括严格/扩展口径、基准、历史净值、当前成分和调仓变化。" asof={`截至 ${animalLatest.date}`}/><section className="stat-grid"><Stat label="动物严格口径" value={num(animalLatest.zoo_strict_nav)} note={pct(asNumber(animalLatest.zoo_strict_daily))} accent/><Stat label="动物扩展口径" value={num(animalLatest.zoo_extended_nav)} note={pct(asNumber(animalLatest.zoo_extended_daily))}/><Stat label="植物严格口径" value={num(plantLatest.zoo_strict_nav)} note={pct(asNumber(plantLatest.zoo_strict_daily))}/><Stat label="沪深300 ETF" value={num(animalLatest.benchmark_nav)} note={pct(asNumber(animalLatest.benchmark_daily))}/></section><Panel title="主题指数净值路径" tag="月度调仓"><LineChart labels={[animalHistory[0]?.date ?? "", animalHistory.at(-1)?.date ?? ""]} series={[{ name: "动物严格", values: animalHistory.map((row) => Number(row.zoo_strict_nav)), color: "#c84b2f" }, { name: "动物扩展", values: animalHistory.map((row) => Number(row.zoo_extended_nav)), color: "#1267d6" }, { name: "植物严格", values: plantHistory.map((row) => Number(row.zoo_strict_nav)), color: "#51855f" }]}/></Panel><div className="research-grid"><Panel title="当前动物成分"><SimpleTable rows={animalConstituents.slice(0, 12)} columns={Object.keys(animalConstituents[0] ?? {}).slice(0, 4).map((key) => [key, key])}/></Panel><Panel title="当前植物成分"><SimpleTable rows={plantConstituents.slice(0, 12)} columns={Object.keys(plantConstituents[0] ?? {}).slice(0, 4).map((key) => [key, key])}/></Panel><Panel title="最近调仓变化"><SimpleTable rows={Object.entries(animalChanges).map(([variant, value]) => ({ variant, detail: JSON.stringify(value) }))} columns={[["variant", "口径"], ["detail", "变化"]]}/></Panel></div></>;
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
  const periodStatus = selected?.status ?? "verified";
  return <section className={`period-panel ${embedded ? "embedded" : ""}`}><div className="period-heading"><div><span className="section-kicker">跨市场小微盘流动性</span><h3>不同时间段，比较小市值股票的可交易性</h3><p>按各市场当期市值分桶，使用滞后 20 日平均成交额；不同市场的覆盖和单位差异保留在状态中。</p></div><span className={`status-badge ${periodStatus}`}>{periodStatus === "verified" ? "已验证" : "覆盖不完整"}</span></div><ControlBar><span className="control-label">时间区间</span>{options.map((value) => { const item = value === "latest" ? null : summary.periods?.find((candidate) => candidate.period === value); return <Choice key={value} active={period === value} onClick={() => setPeriod(value)}>{value === "latest" ? "最新" : value}{item?.status === "incomplete" ? " · 不完整" : ""}</Choice>; })}</ControlBar><div className="period-meta">{selected ? `${selected.common_start ?? "—"} 至 ${selected.common_end ?? "—"} · ${available.length}/${markets.length} 个市场可比` : "当前最新快照 · 以页面顶部数据更新时间为准"}</div>{selected && selected.status === "incomplete" && <div className="callout compact"><span className="section-kicker">覆盖提醒</span><p>该区间不是所有市场都有完整共同覆盖，下面只展示可用市场，不把缺失市场补成零。</p></div>}<div className="period-table"><SimpleTable rows={available.flatMap((market) => market.buckets.map((bucket) => ({ market: market.market, bucket: bucket.label, median_usd: `$${num(bucket.median_usd)}`, mean_usd: `$${num(bucket.mean_usd)}`, observations: num(bucket.observations) })))} columns={[["market", "市场"], ["bucket", "市值分位"], ["median_usd", "成交中位"], ["mean_usd", "成交均值"], ["observations", "观测数"]]} /></div></section>;
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
  return <><ThemeHeading kicker="研究中的专题 · 跨市场流动性" title="流动性需要同时看成交规模、市场结构和数据覆盖。" text="这里是跨市场小微盘流动性的进行中专题；原始行情不发布，公开页面只承载脱敏汇总和明确的数据状态。" asof={`${summary.method.roll_days}日平均 · ${summary.method.currency}`}/><ControlBar><span className="control-label">市场</span><Choice active={market === "all"} onClick={() => setMarket("all")}>全部</Choice>{summary.markets.map((item) => <Choice key={item.market} active={market === item.market} onClick={() => setMarket(item.market)}>{item.market}</Choice>)}<span className="control-label">指标</span><Choice active={metric === "median_usd"} onClick={() => setMetric("median_usd")}>中位数</Choice><Choice active={metric === "mean_usd"} onClick={() => setMetric("mean_usd")}>均值</Choice><Choice active={metric === "p90_usd"} onClick={() => setMetric("p90_usd")}>P90</Choice><Choice active={logScale} onClick={() => setLogScale(!logScale)}>{logScale ? "对数坐标" : "线性坐标"}</Choice></ControlBar><section className="stat-grid">{markets.map((item, index) => <Stat key={item.market} label={`${item.market} · <$100m`} value={`$${num(item.sub_100m_median_usd)}`} note={`${num(item.sub_100m_count)} 只股票`} accent={index === markets.length - 1}/>)}</section><Panel title="小市值股票的流动性中位数" tag={`${metricLabel} · ${logScale ? "对数" : "线性"}`}><BarChart rows={comparison} labelKey="market" valueKey="value" color="#1267d6" formatter={(value) => `$${num(value)}`} logScale={logScale}/></Panel><Panel title="跨市场市值分桶明细" tag="美元成交额"><SimpleTable rows={bucketRows} columns={[["market", "市场"], ["bucket", "市值区间"], ["count", "数量"], ["median_usd", "成交中位"], ["mean_usd", "成交均值"], ["p90_usd", "P90"]]} /></Panel><div className="fine-print"><span className="section-kicker">数据与研究边界</span><p>{summary.caveats.join(" ")}</p></div><div className="research-grid"><article className="research-card"><span className="section-kicker">定义</span><h3>成交额不能直接代表容量</h3><p>页面将名义成交、滞后 ADV、MedADV、参与率和冲击成本拆开，帮助判断实际可执行规模。</p></article><article className="research-card"><span className="section-kicker">时间</span><h3>特征严格滞后一天</h3><p>流动性特征不使用当日成交额，避免把当天结果带入交易前的可投资性判断。</p></article><article className="research-card"><span className="section-kicker">数据边界</span><h3>日股仍待补充同口径快照</h3><p>JPX/J-Quants 适配器已经进入统一 Python 契约，日股分桶结果还要等本地数据完成同口径刷新。</p></article></div></>;
}

function ThemeHeading({ kicker, title, text, asof }: { kicker: string; title: string; text: string; asof: string }) { return <header className="theme-heading"><div><span className="section-kicker">{kicker}</span><h2>{title}</h2><p>{text}</p></div><span className="asof">{asof}</span></header>; }
function SimpleTable({ rows, columns, percentColumns = [] }: { rows: Row[]; columns: string[][]; percentColumns?: string[] }) { return <div className="table-scroll"><table><thead><tr>{columns.map(([key, label]) => <th key={key}>{label}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={`${index}-${row[columns[0]?.[0] ?? ""]}`}>{columns.map(([key]) => <td key={key}>{percentColumns.includes(key) ? pct(asNumber(row[key])) : row[key] === "" || row[key] == null ? "—" : row[key]}</td>)}</tr>)}</tbody></table></div>; }
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
  return <><div className="table-controls"><input aria-label={searchPlaceholder} placeholder={searchPlaceholder} value={query} onChange={(event) => setQuery(event.target.value)}/><span>{visible.length} / {rows.length} 条</span></div><div className="table-scroll"><table><thead><tr>{columns.map(([key, label]) => <th key={key}><button className="table-sort" onClick={() => choose(key)}>{label} {sortKey === key ? (direction === "desc" ? "↓" : "↑") : "↕"}</button></th>)}</tr></thead><tbody>{visible.slice(0, 50).map((row, index) => <tr key={`${index}-${row[columns[0]?.[0] ?? ""]}`}>{columns.map(([key]) => <td key={key}>{percentColumns.includes(key) ? pct(asNumber(row[key])) : row[key] === "" || row[key] == null ? "—" : row[key]}</td>)}</tr>)}</tbody></table></div></>;
}
function Loading() { return <p className="loading">正在加载研究快照……</p>; }

function App() {
  const validTabs: Tab[] = ["overview", "microcap", "style", "cashflow", "cross-market", "indices", "liquidity"];
  const hash = window.location.hash.slice(1) as Tab;
  const [tab, setTab] = useState<Tab>(validTabs.includes(hash) ? hash : "overview");
  const [microcapScope, setMicrocapScope] = useState<MicrocapScope>("a-share");
  useEffect(() => { const onHash = () => { const next = window.location.hash.slice(1) as Tab; if (validTabs.includes(next)) setTab(next); }; window.addEventListener("hashchange", onHash); return () => window.removeEventListener("hashchange", onHash); }, []);
  const [styleScope, setStyleScope] = useState<StyleScope>("indices");
  const page = tab === "microcap" ? <MicrocapPage scope={microcapScope} onScopeChange={setMicrocapScope}/> : tab === "style" ? <StylePage scope={styleScope} onScopeChange={setStyleScope}/> : tab === "indices" ? <IndicesPage/> : tab === "cashflow" ? <CashflowPage/> : tab === "cross-market" || tab === "liquidity" ? <LiquidityPage/> : <Overview/>;
  const navItems: [Tab, string][] = [["overview", "档案总览"], ["cashflow", "现金流历史研究"], ["microcap", "小微盘历史研究"], ["style", "长期风格历史研究"], ["cross-market", "跨市场研究中"]];
  return <div className="app"><header className="site-header"><div className="site-masthead"><div><span className="brand-kicker">历史研究档案 · 证据优先</span><h1>市场研究档案</h1><p className="site-deck">以历史研究为主线，区分已完成证据、进行中专题和待补数据。</p></div><div className="site-meta"><span>历史档案 · 研究中 · 待补数据</span><strong>原始数据外置 · 描述性证据</strong></div></div><nav className="site-nav" aria-label="研究主题">{navItems.map(([key, label]) => <a key={key} className={tab === key || (key === "style" && tab === "indices") || (key === "cross-market" && tab === "liquidity") ? "active" : ""} href={`#${key}`} onClick={() => setTab(key)}>{label}</a>)}</nav></header><main className="site-main">{page}</main><footer className="site-footer"><span>市场研究档案 · 历史证据优先</span><a href="https://github.com/runchengxie/market-research">查看 GitHub 仓库 ↗</a></footer></div>;
}

function Overview() { return <><ThemeHeading kicker="历史研究档案 · 目录" title="先回顾已经形成的证据，再查看正在推进的专题。" text="market-research 以历史市场研究为主线，公开可复核的派生快照；研究中的专题和待补数据会单独标注。" asof="公开快照"/><section className="overview-grid"><a href="#cashflow"><span className="section-kicker">01 · 历史研究</span><h3>现金流历史研究</h3><p>回顾现金流、股息和调仓频率在不同回报口径与持有窗口下的表现。</p><b>进入档案 ↗</b></a><a href="#microcap"><span className="section-kicker">02 · 历史研究</span><h3>小微盘历史研究</h3><p>A股小微盘规则重建与跨市场小微盘流动性，分别通过两个子主题阅读。</p><b>进入档案 ↗</b></a><a href="#style"><span className="section-kicker">03 · 历史研究</span><h3>长期风格历史研究</h3><p>指数、ETF、Barra 和 18 年因子研究，放在同一条历史证据线上。</p><b>进入档案 ↗</b></a><a href="#cross-market"><span className="section-kicker">04 · 研究中的专题</span><h3>跨市场流动性研究</h3><p>比较不同市场小市值尾部的流动性；共同覆盖和日股数据状态会明确展示。</p><b>查看进展 ↗</b></a></section><section className="research-grid"><ResearchCard title="历史研究优先" text="页面首先承载已经完成的市场研究文档和可复核快照，不把未来假设包装成历史事实。"/><ResearchCard title="描述性证据" text="ETF 作为市场代理、指数表现和 18 年因子现象用于描述市场，不等同于 alpha 或策略晋升。"/><ResearchCard title="研究状态优先" text="每个专题保留来源、样本区间和限制条件；日频观察数量不自动等于独立样本数量。"/></section><div className="fine-print"><span className="section-kicker">数据与研究边界</span><p>策略研究、历史市场证据和通用平台能力分开维护；原始行情不发布，跨市场比较不把缺失市场补成零。Global Six-Market 等尚未形成完整快照的内容归入待补数据与未来研究。</p></div></>; }

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
