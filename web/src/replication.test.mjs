import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { readFileSync } from 'node:fs';
import { ReplicationContent, isReplicationSnapshot } from './components/ReplicationSection.tsx';

const data = {
  schema_version: 1, as_of: '2026-09-09',
  sources: [{id: 'study', label: '逐日复刻实验', detail: '固定截点，按252个交易日年化。', url: 'https://example.com/study'}],
  indices: [
    {code: '932368', name: '800现金流', scope: 'cashflow', status: '研究近似', finding: '已有逐日回放。', limitation: '财务修订历史待补。', next: '核对成分。', source_id: 'study'},
    {code: 'wind', name: '万得微盘', scope: 'microcap', status: '数据待补', finding: '日线缺失。', limitation: '暂无复制精度。', next: '补数据。', source_id: 'study'},
  ],
  comparisons: [{scope: 'cashflow', basis: 'price', start: '2021-03-15', end: '2026-09-04', source_id: 'study',
    rows: [{code: '932368', official_cagr: .1227, replica_gross_cagr: .104, replica_net_cagr: .0969, replica_net_max_drawdown: -.227, daily_correlation: .9804, tracking_error: .0399}]}],
};
const render = (scope, snapshot = data) => renderToStaticMarkup(createElement(ReplicationContent, {scope, snapshot}));

test('published snapshot has valid provenance and measurements and all six research subjects', () => {
  const published = JSON.parse(readFileSync(new URL('../public/data/research/replication.json', import.meta.url), 'utf8'));
  assert.equal(isReplicationSnapshot(published), true);
  assert.equal(published.indices.length, 6);
  assert.equal(published.indices.filter(i => i.scope === 'microcap').length, 2);
  assert.equal(published.comparisons.length, 0, '本轮完整组合验证受阻，不发布旧业绩表');
  assert.doesNotMatch(render('cashflow', published), /<table/);
  for (const comparison of published.comparisons) {
    if (comparison.source_id === 'tracking-20260909') {
      for (const row of comparison.rows) {
        assert.equal(row.replica_net_cagr, null, '旧费用路径的净收益已撤回');
        assert.equal(row.replica_net_max_drawdown, null, '旧费用路径的回撤已撤回');
      }
    }
  }
});

test('replication comparison labels its own dates and basis and keeps topic scopes separate', () => {
  const html = render('cashflow');
  assert.match(html, /12\.27%/);
  assert.match(html, /9\.69%/);
  assert.match(html, /-22\.70%/);
  assert.match(html, /2021-03-15/);
  assert.match(html, /价格回报/);
  assert.match(html, /未扣成本复刻与官方收益/);
  assert.match(html, /href="https:\/\/example.com\/study"/);
  assert.doesNotMatch(html, /万得微盘/);
  const micro = render('microcap');
  assert.match(micro, /万得微盘/);
  assert.doesNotMatch(micro, /12\.27%|<table/);
});

test('missing measurements remain unavailable while actual zero remains zero', () => {
  const copy = structuredClone(data);
  copy.comparisons[0].rows[0].daily_correlation = null;
  copy.comparisons[0].rows[0].replica_net_cagr = 0;
  const html = render('cashflow', copy);
  assert.match(html, /未提供/);
  assert.match(html, /0\.00%/);
  assert.doesNotMatch(html, /NaN|undefined/);
});

test('replication snapshot rejects broken provenance, scope, dates and numeric contracts', () => {
  assert.equal(isReplicationSnapshot(data), true);
  for (const mutate of [
    x => x.comparisons[0].source_id = 'missing',
    x => x.sources[0].url = 'javascript:alert(1)',
    x => x.comparisons[0].rows[0].code = 'wind',
    x => x.comparisons[0].rows[0].daily_correlation = 3,
    x => x.comparisons[0].rows[0].replica_gross_cagr = '',
    x => x.comparisons[0].start = '2030-01-01',
    x => x.indices.push({...x.indices[0]}),
  ]) {
    const copy = structuredClone(data); mutate(copy);
    assert.equal(isReplicationSnapshot(copy), false);
  }
});
