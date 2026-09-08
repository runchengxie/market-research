import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Row = Record<string, string>;
type Tab = "overview" | "microcap" | "indices" | "cashflow" | "liquidity";
type Series = { name: string; values: number[]; color: string };
type LiquiditySummary = { method: { roll_days: number; metric: string; currency: string; source_project: string }; markets: { market: string; eligible_stocks: number; sub_100m_count: number; sub_100m_median_usd: number; buckets: { label: string; count: number; median_usd: number; mean_usd: number; p90_usd?: number }[] }[]; caveats: string[] };

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

function LineChart({ series, labels }: { series: Series[]; labels: string[] }) {
  const all = series.flatMap((item) => item.values.filter(Number.isFinite));
  const min = Math.min(...all);
  const max = Math.max(...all);
  const spread = max - min || 1;
  const points = (values: number[]) => values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${96 - ((value - min) / spread) * 82}`).join(" ");
  return <div className="chart"><svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={series.map((item) => item.name).join("、")}><line x1="0" x2="100" y1="14" y2="14" stroke="#ded6c9"/><line x1="0" x2="100" y1="55" y2="55" stroke="#ded6c9"/><line x1="0" x2="100" y1="96" y2="96" stroke="#ded6c9"/>{series.map((item) => <polyline key={item.name} points={points(item.values)} fill="none" stroke={item.color} strokeWidth="1.2" vectorEffect="non-scaling-stroke"/>)}</svg><div className="chart-axis"><span>{labels[0] ?? "—"}</span><div className="legend">{series.map((item) => <span key={item.name}><i style={{ background: item.color }}/>{item.name}</span>)}</div><span>{labels.at(-1) ?? "—"}</span></div></div>;
}

function BarChart({ rows, labelKey, valueKey, color = "#c84b2f", formatter = pct }: { rows: Row[]; labelKey: string; valueKey: string; color?: string; formatter?: (value: number) => string }) {
  const selected = rows.filter((row) => Number.isFinite(asNumber(row[valueKey]))).slice(-24);
  const values = selected.map((row) => asNumber(row[valueKey]));
  const max = Math.max(...values.map((value) => Math.abs(value)), 1);
  return <div className="bar-chart">{selected.map((row) => <div className="bar-row" key={`${row[labelKey]}-${row[valueKey]}`}><span title={row[labelKey]}>{row[labelKey]}</span><div className="bar-track"><i style={{ width: `${Math.min(Math.abs(asNumber(row[valueKey])) / max * 100, 100)}%`, background: asNumber(row[valueKey]) < 0 ? "#8e4d48" : color }}/></div><strong>{formatter(asNumber(row[valueKey]))}</strong></div>)}</div>;
}

function MicrocapPage() {
  const { data: summary } = useJson<Row>("index/microcap/summary.json");
  const { data: reconstructed } = useJson<Row>("index/microcap/reconstructed_summary.json");
  const { data: nav } = useCsv("index/microcap/nav.csv");
  const { data: reconstructedNav } = useCsv("index/microcap/reconstructed_daily_nav.csv");
  const { data: annual } = useCsv("index/microcap/annual_returns.csv");
  const { data: cagr } = useCsv("index/microcap/rolling_cagr.csv");
  const { data: drawdown } = useCsv("index/microcap/rolling_drawdown.csv");
  const { data: underwater } = useCsv("index/microcap/reconstructed_underwater_periods.csv");
  if (!summary || !reconstructed || !nav || !reconstructedNav || !annual || !cagr || !drawdown || !underwater) return <Loading />;
  const latestAnnual = annual.find((row) => row.year === "2025");
  return <><ThemeHeading kicker="微盘规则复现研究 · 完整公开快照" title="收益路径、回撤过程和执行难度，放在同一张图里。" text="这里恢复了 index-research 的公开参考序列、Tushare 规则重建、年度收益、滚动风险和水下区间。" asof={`重建截至 ${reconstructedNav.at(-1)?.date ?? "—"}`}/><section className="stat-grid"><Stat label="公开参考净值" value={num(asNumber(nav.at(-1)?.nav))} note={`截至 ${nav.at(-1)?.date ?? "—"}`} accent/><Stat label="2025年收益" value={pct(asNumber(latestAnnual?.return))} note="公开资料参考"/><Stat label="重建净值" value={num(asNumber(reconstructedNav.at(-1)?.nav))} note="2015年以来日频"/><Stat label="重建最大回撤" value={pct(asNumber(reconstructed.max_drawdown))} note="规则重建"/><Stat label="最长水下" value={`${num(asNumber(reconstructed.longest_underwater_trading_days))} 天`} note={`${reconstructed.longest_underwater_start ?? "—"} 至 ${reconstructed.longest_underwater_end ?? "—"}`}/></section><Panel title="公开参考与规则重建净值" tag="长期路径"><LineChart labels={[nav[0]?.date ?? "", nav.at(-1)?.date ?? ""]} series={[{ name: "公开资料参考", values: nav.map((row) => asNumber(row.nav)), color: "#1267d6" }, { name: "Tushare规则重建", values: reconstructedNav.map((row) => asNumber(row.nav)), color: "#c84b2f" }]}/></Panel><div className="research-grid"><Panel title="年度收益"><BarChart rows={annual} labelKey="year" valueKey="return"/></Panel><Panel title="滚动CAGR"><BarChart rows={cagr} labelKey="window_years" valueKey="cagr" color="#1267d6"/></Panel><Panel title="滚动最大回撤"><BarChart rows={drawdown} labelKey="window_years" valueKey="max_drawdown" color="#8e4d48"/></Panel></div><Panel title="最长水下区间" tag="执行难度"><SimpleTable rows={[...underwater].sort((a, b) => asNumber(b.trading_days) - asNumber(a.trading_days)).slice(0, 10)} columns={[["start_date", "开始"], ["end_date", "结束"], ["trading_days", "交易日"], ["max_drawdown", "最大回撤"]]} percentColumns={["max_drawdown"]}/></Panel><div className="callout"><span className="section-kicker">研究边界</span><p>{reconstructed.caveats ?? "研究重建不等同于 Wind 官方指数；不含交易成本、涨跌停成交限制与资金容量模拟。"}</p></div></>;
}

function IndicesPage() {
  const { data: returns } = useCsv("index/linked_indices/ten_year_price_returns.csv");
  const { data: etfs } = useCsv("index/linked_indices/paired_index_etf_representatives.csv");
  const { data: catalog } = useCsv("index/index_catalog.csv");
  if (!returns || !etfs || !catalog) return <Loading />;
  const top = [...returns].sort((a, b) => asNumber(b.cagr) - asNumber(a.cagr)).slice(0, 12);
  const liquid = etfs.filter((row) => row.liquid_10m === "True").length;
  return <><ThemeHeading kicker="指数长期回报 · ETF可投资性" title="从指数表现到真实产品，把长期回报和可投资性放在一起。" text="恢复 index-research 的指数目录、十年价格回报和 ETF 代表配对结果。价格指数不含分红，ETF 结果受到费用和跟踪误差影响。" asof="静态公开快照"/><section className="stat-grid"><Stat label="指数目录" value={num(catalog.length)} note="已收录公开目录" accent/><Stat label="十年可比指数" value={num(returns.length)} note="有完整起止数据"/><Stat label="ETF代表" value={num(etfs.length)} note="指数配对结果"/><Stat label="流动性通过" value={num(liquid)} note="近60日成交额筛选"/></section><Panel title="十年价格回报最高的指数" tag="前12名"><BarChart rows={top} labelKey="indx_name" valueKey="cagr" color="#1267d6"/></Panel><Panel title="ETF代表：指数与产品的差异" tag="长期复权回报"><SimpleTable rows={etfs.slice(0, 20)} columns={[["ts_code", "ETF"], ["matched_index_name", "跟踪指数"], ["etf_cagr", "ETF年化"], ["index_cagr", "指数年化"], ["etf_max_drawdown", "ETF回撤"], ["median_amount_60d", "60日中位成交额"]]} percentColumns={["etf_cagr", "index_cagr", "etf_max_drawdown"]}/></Panel></>;
}

function CashflowPage() {
  const { data: rows } = useCsv("index/cashflow_indices/cashflow_performance.csv");
  const { data: frequency } = useCsv("index/cashflow_indices/cashflow_rebalance_frequency.csv");
  if (!rows || !frequency) return <Loading />;
  const codes = [...new Set(rows.map((row) => row.ts_code))];
  const oneYear = codes.map((code) => rows.find((row) => row.ts_code === code && row.window === "rolling_1_year") ?? rows.find((row) => row.ts_code === code)).filter((row): row is Row => Boolean(row));
  return <><ThemeHeading kicker="现金流指数 · 股息与调仓研究" title="现金流风格，放在同一套回报和频率口径里比较。" text="恢复现金流指数的多周期表现、回报口径和调仓频率。全收益与价格回报明确分开。" asof={`数据截至 ${rows[0]?.as_of ?? "—"}`}/><section className="stat-grid"><Stat label="指数样本" value={num(codes.length)} note="现金流指数家族" accent/><Stat label="主要调仓" value={frequency[0]?.rebalance_frequency ?? "—"} note="方法论频率"/><Stat label="表现观察窗" value={num(new Set(rows.map((row) => row.window)).size)} note="从近一周到十年"/></section><Panel title="滚动一年累计表现" tag="回报口径可见"><BarChart rows={oneYear} labelKey="name" valueKey="return" color="#1267d6"/></Panel><Panel title="完整表现明细"><SimpleTable rows={rows.filter((row) => row.window === "rolling_1_year" || row.window === "year_2025")} columns={[["name", "指数"], ["rebalance_frequency", "调仓"], ["return_basis", "回报口径"], ["window", "窗口"], ["return", "累计回报"], ["cagr", "年化"]]} percentColumns={["return", "cagr"]}/></Panel></>;
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

function LiquidityPage() {
  const { data: summary } = useJson<LiquiditySummary>("liquidity/summary.json");
  if (!summary) return <Loading />;
  const comparison = summary.markets.map((market) => ({ market: market.market, median: String(market.sub_100m_median_usd), count: String(market.sub_100m_count) }));
  const bucketRows = summary.markets.flatMap((market) => market.buckets.map((bucket) => ({ market: market.market, bucket: bucket.label, count: String(bucket.count), median_usd: String(bucket.median_usd), mean_usd: String(bucket.mean_usd), p90_usd: bucket.p90_usd == null ? "—" : String(bucket.p90_usd) })));
  return <><ThemeHeading kicker="Liquidity Profiles · 跨市场研究" title="流动性不是一个数字，而是可交易规模、市场结构和数据覆盖的组合。" text="market-research 已吸收 liquidity profiles 的面板契约、lagged ADV/MedADV、机械容量和质量诊断。原始行情不发布，公开页面只承载脱敏汇总。" asof={`${summary.method.roll_days}日平均 · ${summary.method.currency}`}/><section className="stat-grid">{summary.markets.map((market, index) => <Stat key={market.market} label={`${market.market} · <$100m`} value={`$${num(market.sub_100m_median_usd)}`} note={`${num(market.sub_100m_count)} 只股票`} accent={index === 2}/>)}</section><Panel title="小市值股票的流动性中位数" tag="近20日平均成交额"><BarChart rows={comparison} labelKey="market" valueKey="median" color="#1267d6" formatter={(value) => `$${num(value)}`}/></Panel><Panel title="跨市场市值分桶明细" tag="USD成交额"><SimpleTable rows={bucketRows} columns={[["market", "市场"], ["bucket", "市值区间"], ["count", "数量"], ["median_usd", "成交中位"], ["mean_usd", "成交均值"], ["p90_usd", "P90"]]} /></Panel><div className="callout"><span className="section-kicker">研究边界</span><p>{summary.caveats.join(" ")}</p></div><div className="research-grid"><article className="research-card"><span className="section-kicker">定义</span><h3>成交额不等于容量</h3><p>页面将名义成交、滞后 ADV、MedADV、参与率和冲击成本拆开，避免用成交额直接代替可执行规模。</p></article><article className="research-card"><span className="section-kicker">时间</span><h3>特征严格滞后一天</h3><p>流动性特征不使用当日成交额，防止把当天结果泄漏进交易前的可投资性判断。</p></article><article className="research-card"><span className="section-kicker">数据边界</span><h3>日股待补同口径快照</h3><p>JPX/J-Quants 适配器已经进入统一 Python 契约，日股分桶结果待本地数据完成同口径刷新。</p></article></div></>;
}

function ThemeHeading({ kicker, title, text, asof }: { kicker: string; title: string; text: string; asof: string }) { return <header className="theme-heading"><div><span className="section-kicker">{kicker}</span><h2>{title}</h2><p>{text}</p></div><span className="asof">{asof}</span></header>; }
function SimpleTable({ rows, columns, percentColumns = [] }: { rows: Row[]; columns: string[][]; percentColumns?: string[] }) { return <div className="table-scroll"><table><thead><tr>{columns.map(([key, label]) => <th key={key}>{label}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={`${index}-${row[columns[0]?.[0] ?? ""]}`}>{columns.map(([key]) => <td key={key}>{percentColumns.includes(key) ? pct(asNumber(row[key])) : row[key] === "" || row[key] == null ? "—" : row[key]}</td>)}</tr>)}</tbody></table></div>; }
function Loading() { return <p className="loading">正在加载研究快照……</p>; }

function App() {
  const validTabs: Tab[] = ["overview", "microcap", "indices", "cashflow", "liquidity"];
  const hash = window.location.hash.slice(1) as Tab;
  const [tab, setTab] = useState<Tab>(validTabs.includes(hash) ? hash : "overview");
  useEffect(() => { const onHash = () => { const next = window.location.hash.slice(1) as Tab; if (validTabs.includes(next)) setTab(next); }; window.addEventListener("hashchange", onHash); return () => window.removeEventListener("hashchange", onHash); }, []);
  const page = tab === "microcap" ? <MicrocapPage/> : tab === "indices" ? <IndicesPage/> : tab === "cashflow" ? <CashflowPage/> : tab === "liquidity" ? <LiquidityPage/> : <Overview/>;
  return <div className="app"><header className="site-header"><div className="site-masthead"><div><span className="brand-kicker">Market Research · 研究项目合并版</span><h1>流动性与指数研究</h1><p className="site-deck">把微盘收益、指数产品和跨市场可交易性放在同一套公开快照里。</p></div><div className="site-meta"><span>替代 index-research</span><strong>吸收 liquidity profiles</strong></div></div><nav className="site-nav" aria-label="研究主题">{[["overview", "研究总览"], ["microcap", "A股微盘"], ["indices", "指数与ETF"], ["cashflow", "现金流指数"], ["liquidity", "跨市场流动性"]].map(([key, label]) => <a key={key} className={tab === key ? "active" : ""} href={`#${key}`} onClick={() => setTab(key as Tab)}>{label}</a>)}</nav></header><main className="site-main">{page}</main><footer className="site-footer"><span>market-research · 原 index-research / market-liquidity-profiles 的合并研究入口</span><a href="https://github.com/runchengxie/market-research">查看 GitHub 仓库 ↗</a></footer></div>;
}

function Overview() { return <><ThemeHeading kicker="统一研究入口 · 吸收旧项目公开内容" title="从收益路径到可交易性，先看全貌，再钻进单个主题。" text="这个项目现在是 index-research 与 liquidity profiles 的合并入口；原始数据仍保留在本地，页面只发布可复核的派生快照。" asof="公开快照"/><section className="overview-grid"><a href="#microcap"><span className="section-kicker">01 · Index Research</span><h3>A股微盘股</h3><p>公开参考净值、规则重建、年度收益、滚动 CAGR、最大回撤和水下区间。</p><b>进入研究 ↗</b></a><a href="#indices"><span className="section-kicker">02 · Index Research</span><h3>指数与ETF</h3><p>十年指数价格回报、指数目录、ETF代表和流动性筛选结果。</p><b>进入研究 ↗</b></a><a href="#liquidity"><span className="section-kicker">03 · Liquidity Profiles</span><h3>跨市场流动性</h3><p>A股、港股、美股统一面板、滞后特征、容量与质量诊断。</p><b>进入研究 ↗</b></a></section><div className="callout"><span className="section-kicker">迁移说明</span><p>旧项目的公开说明和 Pages 将逐步改为指向本页面；旧仓库保留历史代码和提交记录，新项目作为统一发布入口。</p></div></>; }

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
