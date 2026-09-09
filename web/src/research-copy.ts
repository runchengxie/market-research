// Keep original research notes intact in the data files. Translate known prose
// at display time and retain unfamiliar notes for future data versions.
const notes: Record<string, string> = {
  '这是基于本地 Tushare 日线数据的规则重建，不是 Wind 8841431.WI 官方指数。': '这套自制规则使用本地 Tushare 日线数据，与万得微盘官方指数采用不同口径。',
  '使用复权收盘价计算，当前版本未模拟涨跌停无法成交、手续费、印花税、冲击成本和资金容量。': '收益使用复权收盘价计算。涨跌停时能否成交、手续费、印花税、买卖对价格的影响和可交易规模尚未模拟。',
  '调仓信号使用当日总市值，收益从下一交易日收盘价计算，保留了一天的持有滞后。': '按当天总市值选股，收益从下一交易日收盘价开始计算。',
  'A 股日频数据没有记录被省略的停牌日，因此无法仅凭零成交量频率推断停牌情况。': '这批 A 股每日数据省略了部分停牌日。判断停牌情况还需要单独的停牌记录。',
  '这里展示的是机械性的流动性画像，不等同于策略容量或实际执行容量。': '这里汇总股票的成交情况。策略实际能买卖多少，还需结合订单、成本和成交限制判断。',
  '当前历史快照覆盖美国、香港和 A 股；日本仍保留在统一适配器契约中，但目前尚未发布可比的分位桶快照。': '当前统计覆盖美国、香港和 A 股。日本市场已接入数据接口，按相同口径计算的分组统计仍待发布。',
};

export function readableNotes(value: string | string[]) {
  return (Array.isArray(value) ? value : [value]).map(note => notes[note] ?? note).join(' ');
}
