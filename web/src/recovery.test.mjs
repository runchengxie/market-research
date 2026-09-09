import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { RecoveryContent, isRecoverySnapshot } from './components/RecoverySection.tsx';

const series = (ts_code, name, group) => ({
  ts_code, name, group, role: 'baseline', start: '2020-01-02', end: '2020-01-06', observations: 3,
  longest_completed_underwater_calendar_days: null, longest_observed_underwater_calendar_days: 4,
  current_underwater_calendar_days: 4, currently_underwater: true, gain_needed_to_recover: .25,
  episodes: [{ peak_date: '2020-01-02', trough_date: '2020-01-03', recovery_date: null,
    observed_until: '2020-01-06', calendar_days: 4, trading_sessions: 2, censored: true, max_drawdown: -.2 }],
  horizons: [{ years: 1, mature_entries: 0, immature_entries: 3, loss_fraction: null, worst_return: null, median_return: null }],
  entries: [{entry_date: '2020-01-02', breakeven_date: null, observed_until: '2020-01-06', calendar_days: 4, censored: true}],
});
const snapshot = {schema_version: 1, series: [series('932368.CSI', '800现金流', 'cashflow_price'),
  series('gtr', '800现金流（税前全收益）', 'cashflow_gross_total_return'),
  series('883418.TI', '同花顺微盘', 'microcap_vendor_close')], issues: [], excluded: []};
const render = (scope, data = snapshot) => renderToStaticMarkup(createElement(RecoveryContent, {scope, snapshot: data}));

test('cashflow recovery defaults to price series and preserves censoring and immature denominators', () => {
  const html = render('cashflow');
  assert.match(html, /800现金流/);
  assert.doesNotMatch(html, /同花顺微盘|800现金流（税前全收益）/);
  assert.match(html, /至少 4 天/);
  assert.match(html, /25\.00%/);
  assert.match(html, /N\/A/);
  assert.match(html, /期限已满/);
  assert.doesNotMatch(html, /<iframe|NaN|undefined/);
});

test('microcap recovery cannot silently display a cashflow result', () => {
  const html = render('microcap');
  assert.match(html, /同花顺微盘/);
  assert.doesNotMatch(html, /800现金流/);
  assert.match(html, /分红口径/);
});

test('empty or blocked research shows explicit unavailable status, not zero recovery', () => {
  const html = render('cashflow', {...snapshot, series: [], issues: [{group: 'cashflow_price', status: 'blocked_calendar_or_price_gap'}]});
  assert.match(html, /暂无通过校验/);
  assert.match(html, /blocked_calendar_or_price_gap/);
  assert.doesNotMatch(html, /0 天|0\.00%/);
});

test('malformed nested series are rejected before rendering, while null horizons remain valid', () => {
  assert.equal(isRecoverySnapshot(snapshot), true);
  const missing = structuredClone(snapshot);
  delete missing.series[0].episodes;
  assert.equal(isRecoverySnapshot(missing), false);
  const malformed = structuredClone(snapshot);
  malformed.series[0].horizons[0].loss_fraction = 'N/A';
  assert.equal(isRecoverySnapshot(malformed), false);
  assert.equal(isRecoverySnapshot({...snapshot, series: [null]}), false);
});
