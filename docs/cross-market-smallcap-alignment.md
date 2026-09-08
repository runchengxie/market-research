# 跨市场小微盘流动性对齐

跨市场小微盘研究比较“市场 × 市值分位 × 时间区间”，不是把不同市场的
ETF 组合收益混在一起。每个市场在每个观察日重新按当时市值分桶，流动性
使用形成日前 20 个有效观察日的 `ADV20`，展示值统一换算为 USD。

输入来源包括 A 股、HK cold data、Japanese NIRA 和现有美股面板。各来源的
成交额单位、交易日历、停牌记录、可交易 universe 和市值字段不同，因此
输出同时保留 native currency、FX method、universe filter、coverage 和
quality status。

这是一项描述性市场研究。ADV20、低市值分桶和跨市场差异不能直接解释为
策略容量、实际成交能力或生产策略收益。
