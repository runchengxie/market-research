import { useEffect, useState } from 'react';
import { ResearchBarChart } from './ResearchCharts';

type Scope = 'overview' | 'cashflow' | 'microcap';
type Episode = {peak_date: string; trough_date: string; recovery_date: string | null; observed_until: string;
  calendar_days: number; trading_sessions: number; censored: boolean; max_drawdown: number};
type Horizon = {years: number; mature_entries: number; immature_entries: number; loss_fraction: number | null;
  worst_return: number | null; median_return: number | null};
type Entry = {entry_date: string; breakeven_date: string | null; observed_until: string; calendar_days: number; censored: boolean};
type RecoverySeries = {ts_code: string; name: string; group: string; role: string; start: string; end: string; observations: number;
  longest_completed_underwater_calendar_days: number | null; longest_observed_underwater_calendar_days: number;
  currently_underwater: boolean; current_underwater_calendar_days: number; gain_needed_to_recover: number;
  episodes: Episode[]; horizons: Horizon[]; entries: Entry[]};
type Snapshot = {schema_version: number; series: RecoverySeries[]; issues: {group?: string; status: string}[];
  excluded: {ts_code: string; name: string; group: string; status: string}[]};
const groups: Record<string, string> = {cashflow_price: '现金流 · 价格回报', cashflow_gross_total_return: '现金流 · 税前全收益', microcap_vendor_close: '微盘与小盘对照 · 供应商点位'};
const percent = (value: number | null) => value == null || !Number.isFinite(value) ? 'N/A' : `${(value * 100).toFixed(2)}%`;
const days = (value: number | null) => value == null ? 'N/A' : `${value.toLocaleString('zh-CN')} 天`;

export function isRecoverySnapshot(value: unknown): value is Snapshot {
  const object = (item: unknown): item is Record<string, unknown> => item !== null && typeof item === 'object';
  const number = (item: unknown) => typeof item === 'number' && Number.isFinite(item);
  const nullableNumber = (item: unknown) => item === null || number(item);
  const text = (item: unknown) => typeof item === 'string' && item.length > 0;
  const records = (items: unknown, check: (row: Record<string, unknown>) => boolean) => Array.isArray(items) && items.every(item => object(item) && check(item));
  return object(value) && value.schema_version === 1
    && records(value.issues, row => text(row.status) && (row.group === undefined || text(row.group)))
    && records(value.excluded, row => ['ts_code', 'name', 'group', 'status'].every(key => text(row[key])))
    && records(value.series, row => ['ts_code', 'name', 'group', 'role', 'start', 'end'].every(key => text(row[key]))
      && ['observations', 'longest_observed_underwater_calendar_days', 'current_underwater_calendar_days', 'gain_needed_to_recover'].every(key => number(row[key]))
      && nullableNumber(row.longest_completed_underwater_calendar_days) && typeof row.currently_underwater === 'boolean'
      && records(row.episodes, item => ['peak_date', 'trough_date', 'observed_until'].every(key => text(item[key]))
        && (item.recovery_date === null || text(item.recovery_date)) && typeof item.censored === 'boolean'
        && ['calendar_days', 'trading_sessions', 'max_drawdown'].every(key => number(item[key])))
      && records(row.horizons, item => ['years', 'mature_entries', 'immature_entries'].every(key => number(item[key]))
        && ['loss_fraction', 'worst_return', 'median_return'].every(key => nullableNumber(item[key])))
      && records(row.entries, item => text(item.entry_date) && text(item.observed_until)
        && (item.breakeven_date === null || text(item.breakeven_date)) && number(item.calendar_days) && typeof item.censored === 'boolean'));
}

export default function RecoverySection({scope}: {scope: Scope}) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch('./data/research/recovery.json', {signal: controller.signal}).then(response => {
      if (!response.ok) throw new Error('Recovery snapshot unavailable');
      return response.json();
    }).then(value => {
      if (!isRecoverySnapshot(value)) throw new Error('Invalid recovery snapshot');
      setSnapshot(value);
    }).catch(error => { if (error.name !== 'AbortError') setError(true); });
    return () => controller.abort();
  }, []);
  if (error) return <section className="panel" role="alert"><h3>回本与持有期风险</h3><p>回本数据加载失败，请刷新重试；未将缺失结果填为零。</p></section>;
  if (!snapshot) return <section className="panel" role="status">正在加载回本与持有期风险研究…</section>;
  return <RecoveryContent key={scope} scope={scope} snapshot={snapshot}/>;
}

export function RecoveryContent({scope, snapshot}: {scope: Scope; snapshot: Snapshot}) {
  const [group, setGroup] = useState(scope === 'microcap' ? 'microcap_vendor_close' : 'cashflow_price');
  const [code, setCode] = useState(scope === 'microcap' ? '883418.TI' : '932368.CSI');
  const rows = snapshot.series.filter(row => row.group === group);
  const selected = rows.find(row => row.ts_code === code) ?? rows[0];
  const choices = Object.entries(groups).filter(([key]) => scope === 'overview' || (scope === 'microcap' ? key === 'microcap_vendor_close' : key.startsWith('cashflow_')));
  const excluded = snapshot.excluded.filter(row => row.group === group);
  const issues = snapshot.issues.filter(row => !row.group || row.group === group);
  const sorted = selected ? [...selected.episodes].sort((a, b) => b.calendar_days - a.calendar_days) : [];
  // Keep ongoing episodes visible even when they are shorter than the top ten.
  const episodes = sorted.filter((row, index) => index < 10 || row.censored);
  const chartRows = [...episodes].reverse().map(row => ({label: `${row.peak_date}${row.censored ? '（未回本）' : '（已回本）'}`, days: String(row.calendar_days)}));
  return <section className="recovery-section" aria-label="回本与持有期风险">
    <div className="section-heading"><h3>回本与持有期风险</h3><p>{scope === 'overview' ? '跨指数比较：按同口径、同组样本观察，不跨区间混排。' : '除了收益高低，也看买入以后可能等待多久。'}</p></div>
    <div className="panel">
      <div className="control-bar" aria-label="回本研究口径">{choices.map(([value, label]) => <button key={value} className={`choice ${group === value ? 'active' : ''}`} aria-pressed={group === value} onClick={() => setGroup(value)}>{label}</button>)}</div>
      <p className="panel-note">本模块使用完整历史样本，不随其他图表的收益窗口筛选变化。{selected ? `样本 ${selected.start} 至 ${selected.end}，${selected.observations.toLocaleString('zh-CN')} 个交易日观测。` : ''} 水下期均以自然日计；仅识别样本起点之后的高点。</p>
      <p className="panel-note">{group === 'cashflow_price' ? '价格回报不含分红。' : group === 'cashflow_gross_total_return' ? '供应商税前全收益含分红再投资，不代表已独立核验本地分红账本。' : '供应商点位的分红口径尚未独立核验；中证2000、国证2000是小盘对照，不是微盘指数。'} 不计税费、通胀或机会成本；历史包含回溯构建，不等于当时可投资表现，也不能保证未来最长回本期限。</p>
      {issues.length > 0 && <p role="status">校验阻断：{issues.map(row => row.status).join('、')}</p>}
      {excluded.length > 0 && <p className="panel-note">未纳入：{excluded.map(row => `${row.name}（${row.status === 'missing' ? '缺少日线' : '未通过校验'}）`).join('、')}。</p>}
      {group === 'microcap_vendor_close' && <p className="panel-note">旧版自制400股净值存在缺报价估值问题，未纳入本模块。Wind 年度资料不拼接为日频回本序列。</p>}
      {!selected ? <p role="status">暂无通过校验的回本数据，不以零值或其他指数替代。</p> : <>
        <div className="table-scroll"><table><caption>历史最长与当前等待 · {groups[group]}</caption><thead><tr><th>指数</th><th>最长已完成</th><th>最长已观察</th><th>当前水下期</th><th>回本所需涨幅</th><th>样本区间</th></tr></thead><tbody>{rows.map(row => <tr key={row.ts_code}><td>{scope === 'overview' ? <a href={group === 'microcap_vendor_close' ? '#microcap' : '#cashflow'}>{row.name}</a> : row.name}</td><td>{days(row.longest_completed_underwater_calendar_days)}</td><td>{days(row.longest_observed_underwater_calendar_days)}</td><td>{row.currently_underwater ? `至少 ${days(row.current_underwater_calendar_days)}` : '不在水下'}</td><td>{percent(row.gain_needed_to_recover)}</td><td>{row.start} — {row.end}</td></tr>)}</tbody></table></div>
        {scope !== 'overview' && <>
          <label className="recovery-selector">查看指数 <select value={selected.ts_code} onChange={event => setCode(event.target.value)}>{rows.map(row => <option key={row.ts_code} value={row.ts_code}>{row.name}</option>)}</select></label>
          <div className="stat-grid recovery-stats"><Metric label="最长已完成水下期" value={days(selected.longest_completed_underwater_calendar_days)} note="N/A 表示未观察到完整恢复"/><Metric label="当前水下期" value={selected.currently_underwater ? `至少 ${days(selected.current_underwater_calendar_days)}` : '不在水下'} note={`截至 ${selected.end}，未回本时仅为下界`}/><Metric label="回本所需涨幅" value={percent(selected.gain_needed_to_recover)} note="回到样本内历史高点所需涨幅"/></div>
          <h4>水下区间时长 · {selected.name}</h4><p className="panel-note">最长 10 段加仍未恢复区间；横轴为自然日，标签为前期高点日期。已完成与未完成状态单独注明，不能把未完成时长当作最终恢复时间。</p>
          {episodes.length ? <><ResearchBarChart rows={chartRows} labelKey="label" valueKey="days" formatter={value => days(value)}/><div className="table-scroll"><table><caption>水下区间明细</caption><thead><tr><th>前期高点</th><th>谷底</th><th>首次回本 / 观测末日</th><th>状态</th><th>自然日</th><th>交易日</th><th>区间最大回撤</th></tr></thead><tbody>{episodes.map(row => <tr key={row.peak_date}><td>{row.peak_date}</td><td>{row.trough_date}</td><td>{row.recovery_date ?? row.observed_until}</td><td>{row.censored ? '尚未回本（下界）' : '已回本'}</td><td>{row.censored ? '至少 ' : ''}{days(row.calendar_days)}</td><td>{row.trading_sessions}</td><td>{percent(row.max_drawdown)}</td></tr>)}</tbody></table></div></> : <p>样本内未观察到水下区间。</p>}
          <h4>固定持有期的历史结果</h4><p className="panel-note">买入日的 1/3/5/10 周年或之后首个交易日评价；期限未满不参与亏损比例分母。重叠窗口不是独立样本，历史亏损比例不是未来概率。</p>
          <div className="table-scroll"><table><caption>持有期统计 · {selected.name}</caption><thead><tr><th>持有年数</th><th>期限已满</th><th>期限未满</th><th>历史亏损比例</th><th>最差收益</th><th>中位收益</th></tr></thead><tbody>{selected.horizons.map(row => <tr key={row.years}><td>{row.years} 年</td><td>{row.mature_entries}</td><td>{row.immature_entries}</td><td>{percent(row.loss_fraction)}</td><td>{percent(row.worst_return)}</td><td>{percent(row.median_return)}</td></tr>)}</tbody></table></div>
          <details className="recovery-entries"><summary>等待最久的买入日（最多 20 条）</summary><p className="panel-note">首次回本不保证此后一直盈利。最后一个买入日没有后续观测，也标记未回本。</p><div className="table-scroll"><table><thead><tr><th>买入日</th><th>首次回本 / 观测末日</th><th>等待时长</th><th>状态</th></tr></thead><tbody>{selected.entries.map(row => <tr key={row.entry_date}><td>{row.entry_date}</td><td>{row.breakeven_date ?? row.observed_until}</td><td>{row.censored ? '至少 ' : ''}{days(row.calendar_days)}</td><td>{row.censored ? '尚未回本（下界）' : '已回本'}</td></tr>)}</tbody></table></div></details>
        </>}
      </>}
      <p className="panel-note">来源：共享 Tushare 指数日线，经 SSE 交易日历校验后计算的派生统计。仅为描述性研究，不是指数复刻或交易策略。<a href="./research/recovery.html" target="_blank" rel="noreferrer">打开独立报告附件 ↗</a></p>
    </div>
  </section>;
}

function Metric({label, value, note}: {label: string; value: string; note: string}) {
  return <article className="stat"><span>{label}</span><strong>{value}</strong><small>{note}</small></article>;
}
