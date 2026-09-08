# 兼容性与迁移说明

`market-research` 是 canonical、superseding 的统一研究入口；旧项目继续保留历史代码、数据和研究记录，作为 legacy archive，不再承担独立发布职责。

## 现有项目

- `index-research`：微盘公开快照、指数研究页面和历史输出文件的来源。
- `market-liquidity-profiles`：容量适配器、容量数据结构和跨市场流动性结果说明的来源。
- `nira`：JPX、J-Quants 数据及日本市场专用研究流程的来源。

新实现使用小型确定性样本和旧项目纯函数回归测试。完整历史数据的口径比对仍需在有对应本地快照时运行；在该比对完成前，旧项目仍是历史结果的审计参考，不是新的发布入口。

## 输出映射

| Legacy capability | Canonical command/output |
| --- | --- |
| Microcap reconstruction and snapshot | `report microcap`; `microcap/` plus legacy-compatible root files |
| Index price and ETF research | `report indices`; `a_share_index_price_returns.csv` |
| Cash-flow index snapshot | `report cashflow`; `cashflow_indices/` |
| Cross-market liquidity buckets | `report liquidity`; `liquidity_summary.csv` and `liquidity_report.json` |
| Mechanical capacity | `report liquidity`; `capacity_surface.csv` |

Network fetching remains intentionally outside the deterministic core. Fetchers may write derived caches only under configured output roots and must not copy raw market data into Git.

## 当前差异

1. 统一面板保留各市场本币。跨市场换算在后续计算中完成，并在元数据中记录 `currency` 和 `fx_method`。
2. 日股适配器目前没有配套的市值来源。nira 日频数据包含价格、成交量和成交额，但没有总市值，因此日股市值相关报告会标记为 `incomplete`。
3. 微盘重建会展示入选数量和有价格数据的数量，也可以连接滞后流动性诊断。收益规则仍是最小市值 400 只股票等权、下一交易日执行的研究规则。
4. 首阶段报告以静态 JSON 和 CSV 发布，页面使用 `market-research` 的统一前端。
