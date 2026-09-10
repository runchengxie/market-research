import { useEffect, useState } from 'react';
import { isRecoverySnapshot, type Snapshot } from './recovery-data';

type BarraEvidence = {legacy_barra_result?: {coverage_start?: string; coverage_end?: string; factor_count?: number}};
const dayCount = (value: number | null) => value == null ? '尚未观察到完整回本区间' : `${value.toLocaleString('zh-CN')} 个自然日`;

export default function ResearchOverview() {
  const [recovery, setRecovery] = useState<Snapshot | null>(null);
  const [barra, setBarra] = useState<BarraEvidence | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    const read = async (path: string) => {
      const response = await fetch(`./data/${path}`, {signal: controller.signal});
      if (!response.ok) throw new Error('Data unavailable');
      return response.json();
    };
    Promise.allSettled([read('research/recovery.json'), read('barra/barra_summary.json')]).then(([recoveryResult, barraResult]) => {
      if (controller.signal.aborted) return;
      if (recoveryResult.status === 'fulfilled' && isRecoverySnapshot(recoveryResult.value)) setRecovery(recoveryResult.value);
      if (barraResult.status === 'fulfilled' && barraResult.value && typeof barraResult.value === 'object') setBarra(barraResult.value);
      setLoading(false);
    });
    return () => controller.abort();
  }, []);
  if (loading) return <p role="status">正在读取各专题的研究进展…</p>;
  return <OverviewContent recovery={recovery} barra={barra}/>;
}

export function OverviewContent({recovery, barra}: {recovery: Snapshot | null; barra: BarraEvidence | null}) {
  const available = (group: string) => !recovery?.issues.some(issue => !issue.group || issue.group === group);
  const cashflow = available('cashflow_price') ? recovery?.series.find(row => row.ts_code === '932368.CSI' && row.group === 'cashflow_price') : undefined;
  const microcap = available('microcap_vendor_close') ? recovery?.series.find(row => row.ts_code === '883418.TI' && row.group === 'microcap_vendor_close') : undefined;
  const history = barra?.legacy_barra_result;
  const styleAvailable = typeof history?.coverage_end === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(history.coverage_end)
    && typeof history.factor_count === 'number' && Number.isInteger(history.factor_count) && history.factor_count > 0;
  return <>
    <div className="theme-heading"><div><span className="section-kicker">研究总览</span><h2>研究到了哪一步，有哪些发现？</h2><p>先看结论和待解决的问题，再到专题里查看数据、图表与计算方法。</p></div><span className="asof">数据日期按专题分别标注</span></div>
    <section className="featured-study" aria-label="Featured Quant Research study">
      <div>
        <span className="section-kicker">Featured Quant Research</span>
        <h2>18 年 A 股风格因子动态：收益、稳定性与市场阶段</h2>
        <p>这些风格因子在不同 A 股市场阶段是否持续存在？研究使用历史分组收益、年度阶段和相关性来回答这个问题；IC、样本外验证和统计显著性仍待补充。</p>
      </div>
      <a href="#style-factors-18y">阅读旗舰研究 ↗</a>
    </section>
    <section className="evidence-grid" aria-label="各专题研究进展">
      <EvidenceCard title="现金流" href="#cashflow" status={cashflow ? '指数数据已检查' : '数据暂不可用'}
        conclusion={cashflow ? cashflow.longest_completed_underwater_calendar_days == null ? '800现金流价格指数在样本内尚无完整的回本记录。' : `800现金流价格指数在样本内，最长一次从高点跌落后等待了 ${dayCount(cashflow.longest_completed_underwater_calendar_days)}才回本。` : '数据恢复后显示回本统计。'}
        date={cashflow ? `${cashflow.start} 至 ${cashflow.end}` : '数据暂不可用'}
        scope="供应商指数表现，价格回报与税前全收益分开比较。"
        limitation="自行复刻的成分股、权重和财务数据时点仍需验证。"
        next="继续核对官方规则与本地复刻结果。"/>
      <EvidenceCard title="小微盘" href="#microcap" status={microcap ? '参考指数可供研究' : '数据暂不可用'}
        conclusion={microcap ? microcap.longest_completed_underwater_calendar_days == null ? '同花顺微盘在样本内尚无完整的回本记录。' : `同花顺微盘在样本内，最长一次完整回本等待为 ${dayCount(microcap.longest_completed_underwater_calendar_days)}。` : '数据恢复后显示微盘参考指数统计。'}
        date={microcap ? `${microcap.start} 至 ${microcap.end}` : '数据暂不可用'}
        scope="同花顺微盘用于观察微盘表现，中证2000和国证2000作为小盘对照。"
        limitation="自制400股版本有持仓缺报价的问题，收益需要重算。参考指数的分红处理也需核对。"
        next="先补齐估值，再检查停牌、退市与买卖成本。"/>
      <EvidenceCard title="长期风格" href="#style" status={styleAvailable ? '历史结果供研究参考' : '数据暂不可用'}
        conclusion={styleAvailable ? `已整理 ${history.factor_count} 个因子的历史结果，用于观察不同风格在各阶段的表现。` : '数据恢复后显示长期风格研究范围。'}
        date={styleAvailable ? `Barra 历史研究截至 ${history.coverage_end}` : '数据暂不可用'}
        scope="指数和ETF反映市场表现。Barra 多空研究观察高分组与低分组的收益差异。"
        limitation="信号在新数据中是否有效，以及借券、费用和保证金条件仍需验证。"
        next="分别阅读市场走势与因子结果，保留各自的数据口径。"/>
    </section>
    <div className="fine-print"><span className="section-kicker">阅读提示</span><p>各专题的样本时间不同，历史最长等待也会受到样本范围影响。页面保留尚未回本和数据缺失的记录。历史结果仅供研究参考。</p></div>
  </>;
}

function EvidenceCard({title, href, status, conclusion, date, scope, limitation, next}: {
  title: string; href: string; status: string; conclusion: string; date: string; scope: string; limitation: string; next: string;
}) {
  return <article className="evidence-card"><span className="tag warm">{status}</span><h3>{title}</h3><p className="evidence-conclusion">{conclusion}</p>
    <dl><dt>数据范围</dt><dd>{date}</dd><dt>观察什么</dt><dd>{scope}</dd><dt>仍需验证</dt><dd>{limitation}</dd><dt>下一步</dt><dd>{next}</dd></dl><a href={href}>查看{title}专题 ↗</a></article>;
}
