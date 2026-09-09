import test from 'node:test';
import assert from 'node:assert/strict';
import { ResearchBarChart } from './components/ResearchCharts.tsx';

test('bar data keeps absent values missing and retains actual zero returns', () => {
  const chart = ResearchBarChart({rows: ['', ' ', null, undefined, 'NaN', '0', '-0.2'].map(value => ({value, label: 'sample'})), labelKey: 'label', valueKey: 'value'});
  assert.deepEqual(chart.props.option.series[0].data, [null, null, null, null, null, 0, -.2]);
  assert.equal(chart.props.option.tooltip.valueFormatter(null), '未提供');
  assert.equal(chart.props.option.tooltip.valueFormatter(0), '0.0%');
});
