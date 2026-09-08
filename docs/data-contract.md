# 统一市场面板

`market-research` 每行记录一个市场、一个证券和一个交易日，主键为 `(market, symbol, date)`。

必需字段：

```text
market, symbol, date, close, volume, turnover, market_cap,
currency, is_tradable, is_suspended, source
```

适配器保留各市场本币。跨市场换算在后续计算中完成，并在元数据中记录 `currency` 和 `fx_method`。

当前字段映射如下：

| 市场 | 来源字段 | 本币单位 |
|---|---|---|
| A 股 | `trade_date`、`amount`、`total_mv` | 成交额：千元人民币，市值：万元人民币 |
| 港股 | `trade_date`、`total_turnover`、`hk_total_market_val` | 港元 |
| 美股 | `Date`、`Close`、`Volume`、`Shares Outstanding` | 美元 |
| 日股 | `Date`、`Code`、`C`、`Vo`、`Va` | 日元 |

`ADV20`、`MedADV20`、`ADV60` 和 `MedADV60` 都按滞后一个交易日计算。缺失值继续保留为缺失，不能直接当作零成交处理。

每份报告都会记录来源、数据日期、覆盖率、股票池筛选条件、货币、汇率方法、特征滞后期、交易日历模式和数据质量状态。
