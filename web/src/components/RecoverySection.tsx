import { useEffect, useRef, useState } from 'react';
import { ResearchBarChart } from './ResearchCharts';
import { isRecoverySnapshot, type Snapshot } from './recovery-data';
export { isRecoverySnapshot } from './recovery-data';
export type { Snapshot } from './recovery-data';

type Scope = 'cashflow' | 'microcap';
const groups: Record<string, string> = {cashflow_price: '现金流 · 价格回报', cashflow_gross_total_return: '现金流 · 税前全收益', microcap_vendor_close: '微盘与小盘对照 · 供应商点位'};
const percent = (value: number | null) => value == null || !Number.isFinite(value) ? '样本不足' : `${(value * 100).toFixed(2)}%`;
const days = (value: number | null) => value == null ? '尚无完整记录' : `${value.toLocaleString('zh-CN')} 天`;


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
  if (error) return <section className="panel" role="alert"><h3>回本与持有期风险</h3><p>回本数据加载失败，请刷新重试。</p></section>;
  if (!snapshot) return <section className="panel" role="status">正在加载回本与持有期风险研究…</section>;
  return <RecoveryContent key={scope} scope={scope} snapshot={snapshot}/>;
}

export function RecoveryContent({scope, snapshot}: {scope: Scope; snapshot: Snapshot}) {
  const section = useRef<HTMLElement>(null);
  useEffect(() => {
    const scrollToRecovery = () => {
      if (window.location.hash === `#${scope}-recovery`) section.current?.scrollIntoView({block: 'start'});
    };
    scrollToRecovery();
    window.addEventListener('hashchange', scrollToRecovery);
    return () => window.removeEventListener('hashchange', scrollToRecovery);
  }, [scope, snapshot]);
  const [group, setGroup] = useState(scope === 'microcap' ? 'microcap_vendor_close' : 'cashflow_price');
  const [code, setCode] = useState(scope === 'microcap' ? '883418.TI' : '932368.CSI');
  const issues = snapshot.issues.filter(row => !row.group || row.group === group);
  const rows = issues.length ? [] : snapshot.series.filter(row => row.group === group);
  const selected = rows.find(row => row.ts_code === code) ?? rows[0];
  const choices = Object.entries(groups).filter(([key]) => scope === 'microcap' ? key === 'microcap_vendor_close' : key.startsWith('cashflow_'));
  const excluded = snapshot.excluded.filter(row => row.group === group);
  const sorted = selected ? [...selected.episodes].sort((a, b) => b.calendar_days - a.calendar_days) : [];
  // Keep ongoing episodes visible even when they are shorter than the top ten.
  const episodes = sorted.filter((row, index) => index < 10 || row.censored);
  const chartRows = [...episodes].reverse().map(row => ({label: `${row.peak_date}${row.censored ? '（未回本）' : '（已回本）'}`, days: String(row.calendar_days)}));
  return <section ref={section} id={scope === 'cashflow' ? 'cashflow-recovery' : 'microcap-recovery'} className="recovery-section" aria-label="回本与持有期风险">
    <div className="section-heading"><h3>回本与持有期风险</h3><p>买入后多久能回本，长期持有又可能遇到什么风险？</p></div>
    <div className="panel">
      <div className="control-bar" aria-label="回本研究口径">{choices.map(([value, label]) => <button key={value} className={`choice ${group === value ? 'active' : ''}`} aria-pressed={group === value} onClick={() => setGroup(value)}>{label}</button>)}</div>
      <p className="panel-note">这里使用下列完整样本期，与其他图表的短期收益窗口分别查看。{selected ? `样本 ${selected.start} 至 ${selected.end}，${selected.observations.toLocaleString('zh-CN')} 个交易日观测。` : ''} 水下期指指数跌破前期高点后，等待恢复的时间。这里按自然日计算。</p>
      <p className="panel-note">{group === 'cashflow_price' ? '价格回报不含分红。' : group === 'cashflow_gross_total_return' ? '税前全收益计入分红再投资，分红计算沿用数据提供方的结果。' : '分红口径还需核对。中证2000和国证2000用于观察规模稍大的小盘股。'} 统计未计税费、通胀和机会成本。部分历史由指数发布方事后计算，实际投资结果可能不同。</p>
      {issues.length > 0 && <p role="status">部分数据未通过检查，本次暂停展示。{issues.map(row => <code key={row.status}>{row.status}</code>)}</p>}
      {excluded.length > 0 && <p className="panel-note">未纳入：{excluded.map(row => `${row.name}（${row.status === 'missing' ? '缺少日线' : '未通过校验'}）`).join('、')}。</p>}
      {group === 'microcap_vendor_close' && <p className="panel-note">自制400股版本缺少部分持仓报价，收益需要重算。本节回本统计暂不纳入这一版本。万得微盘目前只有年度资料，还不足以计算日频回本等待。</p>}
      {!selected ? <p role="status">暂无通过校验的回本数据，请查看数据检查结果。</p> : <>
        <div className="table-scroll"><table><caption>历史最长与当前等待 · {groups[group]}</caption><thead><tr><th>指数</th><th>最长已完成</th><th>最长已观察</th><th>当前水下期</th><th>回本所需涨幅</th><th>样本区间</th></tr></thead><tbody>{rows.map(row => <tr key={row.ts_code}><td>{row.name}</td><td>{days(row.longest_completed_underwater_calendar_days)}</td><td>{days(row.longest_observed_underwater_calendar_days)}</td><td>{row.currently_underwater ? `至少 ${days(row.current_underwater_calendar_days)}` : '不在水下'}</td><td>{percent(row.gain_needed_to_recover)}</td><td>{row.start} 至 {row.end}</td></tr>)}</tbody></table></div>
        {<>
          <label className="recovery-selector">查看指数 <select value={selected.ts_code} onChange={event => setCode(event.target.value)}>{rows.map(row => <option key={row.ts_code} value={row.ts_code}>{row.name}</option>)}</select></label>
          <div className="stat-grid recovery-stats"><Metric label="最长已完成水下期" value={days(selected.longest_completed_underwater_calendar_days)} note="从前期高点跌落，到首次恢复的最长记录"/><Metric label="当前水下期" value={selected.currently_underwater ? `至少 ${days(selected.current_underwater_calendar_days)}` : '不在水下'} note={`截至 ${selected.end}，未回本时仅为下界`}/><Metric label="回本所需涨幅" value={percent(selected.gain_needed_to_recover)} note="回到样本内历史高点所需涨幅"/></div>
          <h4>水下区间时长 · {selected.name}</h4><p className="panel-note">显示等待最久的10个区间，并保留尚未回本的区间。横轴为自然日，左侧标注前期高点日期。尚未回本的记录只表示截至样本末已等待的时间。</p>
          {episodes.length ? <><ResearchBarChart rows={chartRows} labelKey="label" valueKey="days" formatter={value => days(value)}/><div className="table-scroll"><table><caption>水下区间明细</caption><thead><tr><th>前期高点</th><th>谷底</th><th>首次回本或样本末日</th><th>状态</th><th>自然日</th><th>交易日</th><th>区间最大回撤</th></tr></thead><tbody>{episodes.map(row => <tr key={row.peak_date}><td>{row.peak_date}</td><td>{row.trough_date}</td><td>{row.recovery_date ?? row.observed_until}</td><td>{row.censored ? '尚未回本' : '已回本'}</td><td>{row.censored ? '至少 ' : ''}{days(row.calendar_days)}</td><td>{row.trading_sessions}</td><td>{percent(row.max_drawdown)}</td></tr>)}</tbody></table></div></> : <p>样本内未观察到水下区间。</p>}
          <h4>固定持有期的历史结果</h4><p className="panel-note">分别观察买入后1年、3年、5年和10年的结果。期限未满的记录单列。历史亏损比例只计算期限已满的记录，供回顾历史时参考。</p>
          <div className="table-scroll"><table><caption>持有期统计 · {selected.name}</caption><thead><tr><th>持有年数</th><th>期限已满</th><th>期限未满</th><th>历史亏损比例</th><th>最差收益</th><th>中位收益</th></tr></thead><tbody>{selected.horizons.map(row => <tr key={row.years}><td>{row.years} 年</td><td>{row.mature_entries}</td><td>{row.immature_entries}</td><td>{percent(row.loss_fraction)}</td><td>{percent(row.worst_return)}</td><td>{percent(row.median_return)}</td></tr>)}</tbody></table></div>
          <details className="recovery-entries"><summary>等待最久的买入日（最多 20 条）</summary><p className="panel-note">首次回本不保证此后一直盈利。最后一个买入日没有后续观测，也标记未回本。</p><div className="table-scroll"><table><thead><tr><th>买入日</th><th>首次回本或样本末日</th><th>自然日</th><th>交易日</th><th>回本前最差收益</th><th>状态</th></tr></thead><tbody>{selected.entries.map(row => <tr key={row.entry_date}><td>{row.entry_date}</td><td>{row.breakeven_date ?? row.observed_until}</td><td>{row.censored ? '至少 ' : ''}{days(row.calendar_days)}</td><td>{row.trading_sessions}</td><td>{percent(row.worst_return_before_breakeven)}</td><td>{row.censored ? '尚未回本' : '已回本'}</td></tr>)}</tbody></table></div></details>
        </>}
      </>}
      <details className="recovery-method"><summary>计算方法与阅读提示</summary>
        <p>水下期从前期高点算起，到指数首次恢复至该高点为止，达到相同点位就算回本。自然日是两个日期相差的天数，交易日数按两个日期之间相隔的交易日计算。</p>
        <p>最长已完成统计已回本的区间。最长已观察也包括尚未回本的区间。尚未回本时，等待天数只是当前记录，未来还可能继续增加。</p>
        <p>逐日买入统计从买入后的下一个交易日起寻找首次回本日期。样本最后一天没有后续数据，也记为尚未回本。回本后仍可能再次亏损。</p>
        <p>固定持有期在买入日满1年、3年、5年或10年后的首个交易日计算，周年当天开市就采用当天。期限未满时显示样本不足。相邻买入日的持有期高度重叠，历史亏损比例不能直接用来预测未来。</p>
        <p>回本所需涨幅等于前期高点除以当前点位，再减1。例如下跌50%后，需要上涨100%才能回本。</p>
        <p>样本开始前的高点无法识别。历史最长等待不保证未来也能在同样时间内回本。价格指数不含分红，税前全收益计入分红再投资。税费、通胀、机会成本和实际买卖限制尚未计入。</p>
        <p>来源为 Tushare 指数日线，交易日期已按上交所日历检查。这里只展示计算后的统计，完整输入和检查记录保存在研究环境中。</p>
      </details>
      <p className="panel-note"><a href={scope === 'cashflow' ? '#microcap-recovery' : '#cashflow-recovery'}>查看{scope === 'cashflow' ? '小微盘' : '现金流'}回本研究 ↗</a></p>
    </div>
  </section>;
}

function Metric({label, value, note}: {label: string; value: string; note: string}) {
  return <article className="stat"><span>{label}</span><strong>{value}</strong><small>{note}</small></article>;
}
