import { StrictMode, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type NavRow = { date: string; nav: number; daily_return: number; constituents: number };
type Summary = { source_label: string; method: string; observations: number; max_drawdown: number; longest_underwater_trading_days: number; longest_underwater_start: string; longest_underwater_end: string; caveats: string[] };
type Manifest = { generated_at: string; sources: string[]; markets: Record<string, string>; privacy: string };

const pct = (value: number | null | undefined) => value == null || Number.isNaN(value) ? "—" : `${(value * 100).toFixed(1)}%`;
const number = (value: number | null | undefined) => value == null || Number.isNaN(value) ? "—" : new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(value);

function useJson<T>(name: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { fetch(`./data/${name}.json`).then((response) => { if (!response.ok) throw new Error(`${response.status}`); return response.json() as Promise<T>; }).then(setData).catch((reason: Error) => setError(reason.message)); }, [name]);
  return { data, error };
}

function Stat({ label, value, note, accent = false }: { label: string; value: string; note: string; accent?: boolean }) {
  return <article className={`stat ${accent ? "accent" : ""}`}><span>{label}</span><strong>{value}</strong><small>{note}</small></article>;
}

function NavChart({ rows }: { rows: NavRow[] }) {
  const points = useMemo(() => {
    if (!rows.length) return "";
    const min = Math.min(...rows.map((row) => row.nav));
    const max = Math.max(...rows.map((row) => row.nav));
    const spread = max - min || 1;
    return rows.map((row, index) => `${(index / Math.max(rows.length - 1, 1)) * 100},${96 - ((row.nav - min) / spread) * 82}`).join(" ");
  }, [rows]);
  return <div className="chart" aria-label="微盘股规则重建净值曲线"><svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img"><defs><linearGradient id="fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#d65a3a" stopOpacity=".34"/><stop offset="1" stopColor="#d65a3a" stopOpacity="0"/></linearGradient></defs><polyline points={`0,100 ${points} 100,100`} fill="url(#fill)" stroke="none"/><polyline points={points} fill="none" stroke="#c84b2f" strokeWidth="1.1" vectorEffect="non-scaling-stroke"/></svg><div className="chart-axis"><span>{rows[0]?.date ?? "—"}</span><strong>净值 {number(rows.at(-1)?.nav)}</strong><span>{rows.at(-1)?.date ?? "—"}</span></div></div>;
}

function App() {
  const { data: summary, error: summaryError } = useJson<Summary>("microcap_summary");
  const { data: nav, error: navError } = useJson<NavRow[]>("microcap_nav");
  const { data: manifest } = useJson<Manifest>("manifest");
  const [tab, setTab] = useState("overview");
  const latest = nav?.at(-1);
  const navReturn = nav && nav.length > 1 ? latest!.nav / nav[0].nav - 1 : null;
  const loading = !summary || !nav;
  const error = summaryError || navError;
  return <div className="app"><header className="site-header"><div className="site-masthead"><div><span className="brand-kicker">Market Research · 公开研究快照</span><h1>流动性与微盘股研究</h1><p className="site-deck">把市场结构、可交易性和收益路径放在同一张桌面上。</p></div><div className="site-meta"><span>静态研究看板</span><strong>数据优先，口径清楚</strong></div></div><nav className="site-nav" aria-label="研究主题"><button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}>研究总览</button><button className={tab === "microcap" ? "active" : ""} onClick={() => setTab("microcap")}>A股微盘</button><button className={tab === "liquidity" ? "active" : ""} onClick={() => setTab("liquidity")}>跨市场流动性</button></nav></header><main className="site-main">{loading ? <p className="loading">正在加载研究快照……</p> : error ? <p className="load-error">数据加载失败：{error}</p> : tab === "liquidity" ? <Liquidity manifest={manifest}/> : <><header className="theme-heading"><div><span className="section-kicker">A股微盘规则复现 · 研究快照</span><h2>{tab === "overview" ? "最小市值不只是收益问题，也是交易与容量问题。" : "在最小市值股票里，收益路径和执行难度必须一起看。"}</h2><p>{summary!.method}。这是一份研究重建，不等同于 Wind 官方指数。</p></div><span className="asof">截至 {latest?.date}</span></header><section className="stat-grid"><Stat label="样本交易日" value={number(summary!.observations)} note="本地规则重建" accent/><Stat label="重建净值" value={number(latest?.nav)} note="起点 = 1"/><Stat label="样本期收益" value={pct(navReturn)} note={`${nav?.[0]?.date} 至 ${latest?.date}`}/><Stat label="最大回撤" value={pct(summary!.max_drawdown)} note="历史日频路径"/><Stat label="最长水下" value={`${number(summary!.longest_underwater_trading_days)} 天`} note={`${summary!.longest_underwater_start} 至 ${summary!.longest_underwater_end}`}/></section><div className="callout"><span className="section-kicker">研究提示</span><p>A股即使在市值排名末端，通常仍有可观的名义成交额；但“有成交”不等于“容易按目标价格成交”。小盘股研究应把流动性、涨跌停、停牌、冲击成本和容量单独拆开。</p></div><section className="section-heading"><h3>收益路径</h3><p>净值曲线展示规则重建的历史路径；它不包含交易成本，也没有模拟真实资金规模下的策略容量。</p></section><div className="panel"><div className="panel-title"><h3>最小 400 只市值股票 · 等权重建</h3><span className="tag warm">可公开快照</span></div><NavChart rows={nav ?? []}/></div><section className="research-grid"><article className="research-card"><span className="section-kicker">口径</span><h3>研究重建，不是官方指数</h3><p>{summary!.caveats[0]}</p></article><article className="research-card"><span className="section-kicker">容量</span><h3>机械容量 ≠ 策略容量</h3><p>{summary!.caveats[1]}</p></article><article className="research-card"><span className="section-kicker">下一步</span><h3>接入跨市场 profile</h3><p>同一套面板将逐步接入港股、美股和日股，比较成交额、ADV、MedADV 与可参与资金规模。</p></article></section></>}</main><footer className="site-footer"><span>{manifest?.privacy ?? "静态研究快照 · 仅供研究参考"}</span><a href="https://github.com/runchengxie/market-research">查看 GitHub 仓库 ↗</a></footer></div>;
}

function Liquidity({ manifest }: { manifest: Manifest | null }) {
  return <><header className="theme-heading"><div><span className="section-kicker">Liquidity Profiles · 跨市场研究</span><h2>统一面板正在连接四个市场的数据口径。</h2><p>这里保留市场状态与数据边界，避免把尚未刷新或不可公开的数据误读成零。</p></div><span className="asof">静态快照</span></header><div className="market-grid">{Object.entries(manifest?.markets ?? {}).map(([market, status]) => <article className="market-card" key={market}><span>{market.replace("a_share", "A股").toUpperCase()}</span><strong className={status === "published" ? "ready" : "pending"}>{status === "published" ? "已发布" : "待本地刷新"}</strong><small>{status === "published" ? "已生成脱敏研究快照" : "原始数据保留在本地研究环境"}</small></article>)}</div><div className="callout"><span className="section-kicker">数据边界</span><p>GitHub Pages 只承载派生结果，不承载移动硬盘中的原始行情、券商数据或 API 凭证。跨市场 liquidity profile 计算完成后，会以同样的方式进入这个页面。</p></div></>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
