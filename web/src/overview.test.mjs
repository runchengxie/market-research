import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { OverviewContent } from './components/ResearchOverview.tsx';

const recovery = JSON.parse(readFileSync(new URL('../public/data/research/recovery.json', import.meta.url)));
const barra = JSON.parse(readFileSync(new URL('../public/data/barra/barra_summary.json', import.meta.url)));

test('overview dates and representative observations come from the corresponding evidence', () => {
  const html = renderToStaticMarkup(createElement(OverviewContent, {recovery, barra}));
  assert.match(html, /2026-09-04/);
  assert.match(html, /2026-08-14/);
  assert.match(html, /1,073/);
  assert.match(html, /308/);
  assert.match(html, /href="#cashflow"/);
  assert.match(html, /href="#microcap"/);
  assert.match(html, /href="#style"/);
  assert.match(html, /18 年 A 股风格因子动态/);
  assert.match(html, /href="#style-factors-18y"/);
  assert.match(html, /收益、稳定性与市场阶段/);
  assert.doesNotMatch(html, /-22\.16|独立报告|recovery\.html|<table|<select|research-chart/);
});

test('missing evidence does not retain dated conclusions or imply validation', () => {
  const html = renderToStaticMarkup(createElement(OverviewContent, {recovery: null, barra: null}));
  assert.doesNotMatch(html, /1,073|308|2026-09-04|2026-08-14/);
  assert.match(html, /数据暂不可用/);
  assert.match(html, /仍需验证/);
});

test('overview does not present blocked groups as checked', () => {
  const blocked = {...recovery, series: [], issues: [{group: 'cashflow_price', status: 'blocked_calendar_or_price_gap'}]};
  const html = renderToStaticMarkup(createElement(OverviewContent, {recovery: blocked, barra: null}));
  assert.match(html, /数据暂不可用/);
  assert.doesNotMatch(html, /1,073|308/);
});

test('representative code with mismatched return basis is not described as price evidence', () => {
  const wrong = structuredClone(recovery);
  wrong.series.find(row => row.ts_code === '932368.CSI').group = 'cashflow_gross_total_return';
  const html = renderToStaticMarkup(createElement(OverviewContent, {recovery: wrong, barra: null}));
  assert.doesNotMatch(html, /1,073/);
  assert.match(html, /数据暂不可用/);
});
