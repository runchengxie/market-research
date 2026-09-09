import { useEffect, useState } from 'react';

type Scope = 'cashflow' | 'microcap';
type Measurement = {
  code: string; official_cagr: number | null; replica_gross_cagr: number | null;
  replica_net_cagr: number | null; replica_net_max_drawdown: number | null;
  daily_correlation: number | null; tracking_error: number | null;
};
type Snapshot = {
  schema_version: 1; as_of: string;
  sources: {id: string; label: string; detail: string; url: string}[];
  indices: {code: string; name: string; scope: Scope; status: string; finding: string; limitation: string; next: string; source_id: string}[];
  comparisons: {scope: Scope; basis: 'price' | 'total'; start: string; end: string; source_id: string; rows: Measurement[]}[];
};
const isObject = (x: unknown): x is Record<string, unknown> => x !== null && typeof x === 'object';
const nonempty = (x: unknown): x is string => typeof x === 'string' && x.trim().length > 0;
const date = (x: unknown): x is string => typeof x === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(x) && Number.isFinite(Date.parse(x)) && new Date(x).toISOString().slice(0, 10) === x;
const finiteOrNull = (x: unknown): x is number | null => x === null || typeof x === 'number' && Number.isFinite(x);
const scope = (x: unknown) => x === 'cashflow' || x === 'microcap';

export function isReplicationSnapshot(x: unknown): x is Snapshot {
  if (!isObject(x) || x.schema_version !== 1 || !date(x.as_of) || !Array.isArray(x.sources) || !Array.isArray(x.indices) || !Array.isArray(x.comparisons)) return false;
  if (!x.sources.every(s => isObject(s) && ['id', 'label', 'detail'].every(k => nonempty(s[k])) && typeof s.url === 'string' && /^https:\/\//.test(s.url))) return false;
  const sourceIds = new Set(x.sources.map(s => s.id));
  if (sourceIds.size !== x.sources.length) return false;
  if (!x.indices.every(i => isObject(i) && scope(i.scope) && ['code', 'name', 'status', 'finding', 'limitation', 'next'].every(k => nonempty(i[k])) && sourceIds.has(i.source_id))) return false;
  const indexScope = new Map(x.indices.map(i => [i.code, i.scope]));
  if (indexScope.size !== x.indices.length) return false;
  return x.comparisons.every(g => isObject(g) && scope(g.scope) && ['price', 'total'].includes(String(g.basis))
    && date(g.start) && date(g.end) && g.start < g.end && g.end <= String(x.as_of)
    && sourceIds.has(g.source_id) && Array.isArray(g.rows) && g.rows.length > 0
    && new Set(g.rows.map(r => isObject(r) ? r.code : null)).size === g.rows.length
    && g.rows.every(r => isObject(r) && indexScope.get(r.code) === g.scope
      && ['official_cagr', 'replica_gross_cagr', 'replica_net_cagr', 'replica_net_max_drawdown', 'daily_correlation', 'tracking_error'].every(k => finiteOrNull(r[k]))
      && ['official_cagr', 'replica_gross_cagr', 'replica_net_cagr'].every(k => r[k] === null || Number(r[k]) >= -1)
      && (r.daily_correlation === null || Math.abs(Number(r.daily_correlation)) <= 1)
      && (r.tracking_error === null || Number(r.tracking_error) >= 0)
      && (r.replica_net_max_drawdown === null || Number(r.replica_net_max_drawdown) >= -1 && Number(r.replica_net_max_drawdown) <= 0)));
}

export default function ReplicationSection({scope}: {scope: Scope}) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    fetch('./data/research/replication.json', {signal: controller.signal})
      .then(r => { if (!r.ok) throw new Error('Unavailable'); return r.json(); })
      .then(data => { if (!controller.signal.aborted && isReplicationSnapshot(data)) setSnapshot(data); })
      .catch(() => {})
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);
  if (loading) return <p role="status">正在读取复刻研究…</p>;
  if (!snapshot) return <section className="panel" role="status">复刻研究数据暂不可用，请稍后重试。其他专题数据仍可查看。</section>;
  return <ReplicationContent scope={scope} snapshot={snapshot}/>;
}

const pct = (x: number | null) => x === null ? '未提供' : `${(x * 100).toFixed(2)}%`;
export function ReplicationContent({scope, snapshot}: {scope: Scope; snapshot: Snapshot}) {
  const indices = snapshot.indices.filter(i => i.scope === scope);
  const comparisons = snapshot.comparisons.filter(g => g.scope === scope);
  const sources = snapshot.sources.filter(s => indices.some(i => i.source_id === s.id) || comparisons.some(g => g.source_id === s.id));
  return <section className="replication-section" aria-label="指数复刻进展">
    <div className="theme-heading"><div><span className="section-kicker">指数复刻</span><h2>我们自己算出的结果，跟指数有多接近？</h2><p>这里单独记录本地选股和持仓回放的结果。完整指数与少量股票组合需要分别验证。</p></div><span className="asof">研究更新 {snapshot.as_of}</span></div>
    <div className="evidence-grid">{indices.map(i => <article className="evidence-card" key={i.code}><span className="tag warm">{i.status}</span><h3>{i.name}</h3><p>{i.finding}</p><dl><dt>仍需解决</dt><dd>{i.limitation}</dd><dt>下一步</dt><dd>{i.next}</dd></dl><a href={snapshot.sources.find(s => s.id === i.source_id)?.url}>查看来源与方法 ↗</a></article>)}</div>
    {comparisons.map(g => <section className="panel" key={`${g.basis}-${g.start}-${g.end}`}>
      <h3>{g.basis === 'price' ? '价格回报' : '税前全收益'}复刻对照</h3>
      <p className="panel-note">{g.start} 至 {g.end}。本表使用固定实验区间，不随其他图表筛选变化。年化按252个交易日计算，扣成本结果采用25基点成交成本模型，尚未完整模拟实际成交限制。</p>
      <div className="table-scroll"><table><thead><tr>{['指数', '官方年化', '复刻年化（未扣成本）', '复刻年化（扣成本）', '复刻最大回撤（扣成本）', '日收益相关性', '年化跟踪误差'].map(h => <th key={h}>{h}</th>)}</tr></thead><tbody>{g.rows.map(r => <tr key={r.code}><td>{indices.find(i => i.code === r.code)?.name}</td><td>{pct(r.official_cagr)}</td><td>{pct(r.replica_gross_cagr)}</td><td>{pct(r.replica_net_cagr)}</td><td>{pct(r.replica_net_max_drawdown)}</td><td>{r.daily_correlation === null ? '未提供' : r.daily_correlation.toFixed(4)}</td><td>{pct(r.tracking_error)}</td></tr>)}</tbody></table></div>
      <p className="panel-note">相关性与跟踪误差均比较未扣成本复刻与官方收益。相关性越接近1，日常涨跌越相似。跟踪误差衡量收益差的波动，数值越小越稳定。两项指标都要结合长期收益差判断。来源：{snapshot.sources.find(s => s.id === g.source_id)?.label}。</p>
    </section>)}
    <details className="panel"><summary>数据来源与研究边界</summary>{sources.map(s => <p key={s.id}><a href={s.url}>{s.label} ↗</a>：{s.detail}</p>)}<p>历史包含回溯构建，尚未补齐的数据会影响结论。这些结果只支持研究与模拟评估，不能作为飞书少量选股组合的业绩证明。</p></details>
  </section>;
}
