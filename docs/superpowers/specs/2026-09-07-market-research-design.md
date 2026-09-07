# market-research 统一市场研究框架设计

**日期：** 2026-09-07  
**状态：** 待用户审核  
**关联项目：** `index-research`、`market-liquidity-profiles`、`nira`

## 1. 目标

创建一个新的 `market-research` 顶层研究项目，统一 A 股、港股、美股和日股的：

- 市场数据适配与数据质量检查；
- 流动性分布与容量诊断；
- 指数、微盘股和风格组合研究；
- 理论收益与真实可执行收益的比较；
- 可复现的跨市场报告和静态研究页面。

新项目是研究编排和公共接口层，不是原始数据仓库。原始数据继续由现有本地数据资产维护，研究结果只保存可复现的派生文件和小型快照。

## 2. 非目标

- 第一阶段不重建 Tushare、SimFin、RQData 或 J-Quants 数据下载系统；
- 不把原始 Parquet、CSV、分钟数据或逐笔数据提交到新 Git 仓库；
- 不立即删除、重命名或破坏 `index-research`、`market-liquidity-profiles` 或 `nira`；
- 不把机械容量上限解释成策略实际容量；
- 不在第一阶段实现完整的组合成交模拟、盘口冲击模型或实盘下单。

## 3. 推荐架构

```text
market-research/
├── src/market_research/
│   ├── contracts/       # 统一面板、来源元数据、质量状态
│   ├── markets/         # A股、港股、美股、日股输入适配器
│   ├── liquidity/       # ADV、MedADV、分桶、流动性画像
│   ├── capacity/        # 参与率、期限、机械容量和压力窗口
│   ├── indexes/         # 指数规则、微盘重建、收益和回撤
│   ├── reports/         # 跨市场比较和报告数据集
│   └── cli.py           # 统一命令入口
├── configs/             # 数据根路径和研究参数，不含机器身份信息
├── tests/
├── outputs/             # 可发布的小型派生快照
├── notebooks/           # 可选的可审计分析记录
├── site/                # 后续迁移 index-research 页面
└── docs/
```

模块边界如下：

| 模块 | 责任 | 不负责 |
|---|---|---|
| `contracts` | 定义统一字段、单位、币种、来源和时间截点 | 下载数据、推断缺失值 |
| `markets` | 把各市场原始数据转换成统一日频面板 | 跨市场排名和研究结论 |
| `liquidity` | 成交额统计、分位数、低流动性尾部 | 指数收益计算 |
| `capacity` | 使用滞后流动性计算参与率/期限下的机械容量 | 成交撮合和实际 NAV |
| `indexes` | 指数规则、成分、净值、回撤和重建 | 统一原始数据路径 |
| `reports` | 合并各模块输出并生成研究快照 | 修改底层数据 |

`market-liquidity-profiles` 的容量和适配逻辑是迁移来源，`index-research` 的微盘重建和指数分析是迁移来源，`nira` 仅作为日股数据与字段参考来源，不复制整个日股策略项目。

## 4. 统一数据契约

所有市场适配器输出一行一个 `(market, symbol, date)` 的日频面板。第一阶段的规范字段为：

| 字段 | 类型 | 含义 |
|---|---|---|
| `market` | string | `a_share`、`hk`、`us`、`jp` |
| `symbol` | string | 市场内稳定代码 |
| `date` | date | 市场交易日 |
| `close` | float | 收盘价，原生币种 |
| `volume` | float | 成交量，保留来源单位说明 |
| `turnover` | float | 成交额，原生币种 |
| `market_cap` | float | 总市值，原生币种 |
| `currency` | string | `CNY`、`HKD`、`USD`、`JPY` |
| `is_tradable` | bool | 研究口径下是否可交易 |
| `is_suspended` | bool | 是否停牌或缺少有效成交 |
| `source` | string | 数据源或数据快照标识 |

派生的标准化容量字段可以使用 `notional_volume`，但必须同时保留 `currency` 和 `fx_method`。跨市场比较默认换算为 USD；A 股历史容量研究可以保留原生 CNY，并在元数据中明确声明。

每个输出还必须携带：`as_of`、`coverage_start`、`coverage_end`、`universe_filter`、`feature_lag`、`calendar_mode` 和 `quality_status`。

关键规则：

1. `ADV20`、`MedADV20`、`ADV60` 和 `MedADV60` 只能使用截至前一交易日的数据；
2. 缺失观察不能自动等价为零成交；
3. 日线接口没有返回的交易日必须在质量诊断中区分“缺失”和“明确零成交”；
4. A 股 `amount` 按千元转换为元，`total_mv` 按万元转换为元；
5. 适配器的过滤条件、汇率方法和时间截点必须进入报告元数据。

## 5. 市场适配器

### A 股

复用现有 `market-liquidity-profiles` 的 Tushare daily-clean 适配逻辑，支持当前快照和历史容量模式。历史模式必须保留点时成分、显式交易日历、停牌和缺失覆盖诊断。

### 港股

复用现有 RQData 适配逻辑，使用 `total_turnover`、`hk_total_market_val` 和 Active/non-ETF 过滤。固定汇率只能作为默认配置，报告必须记录该假设。

### 美股

复用 SimFin 的 `Close × Volume` 成交额和 `Close × Shares Outstanding` 市值计算。必须保留非仙股过滤条件，并明确最近 20 个有成交交易日与自然日窗口的区别。

### 日股

从 `/mnt/data/cold4t/nira/current/guan-japanese-nira/data` 读取 J-Quants/JPX 日线和 master 数据。第一阶段只需要日线、成交量/成交额、上市状态和基础 master 字段；分钟、逐笔、融资融券和因子结果不进入第一版跨市场容量面板。

日股适配器必须处理 JPY 原生单位，并通过配置提供 JPY/USD 汇率来源。不能直接假设日股字段与 Tushare 或 SimFin 同名同义。

## 6. 研究数据流

```text
原始数据目录
    ↓
market adapters
    ↓
统一日频面板 + provenance metadata
    ↓
quality checks
    ↓
liquidity features (ADV/MedADV/percentile)
    ↓
capacity surface / stress windows
    ↓
index reconstruction + return/drawdown
    ↓
cross-market report snapshot + site data
```

指数研究和流动性研究通过统一面板和明确的 `(market, symbol, date)` 粒度连接，不直接互相读取对方的私有中间文件。

## 7. 第一阶段交付范围

第一阶段完成一个可运行的跨市场研究最小闭环：

1. 新项目具备 Python 包、配置、CLI、测试和数据路径说明；
2. A股、港股、美股适配器迁移到统一契约；
3. 日股适配器读取 `nira` 的日线和 master 数据；
4. 四市场输出统一的最新截面流动性分桶；
5. 输出 ADV20/MedADV20、市场规模分桶、低流动性尾部和机械容量；
6. 将 A股微盘规则重建接入统一面板，保留研究重建而非 Wind 官方指数的标签；
7. 生成一份跨市场 Markdown/CSV/JSON 研究快照；
8. 对原始缺失、幸存者偏差、停牌处理、汇率和容量含义给出机器可读元数据和人工说明。

第一阶段暂不迁移完整前端。现有 `index-research` 页面继续运行；跨市场报告先输出静态数据和 Markdown，第二阶段再决定是否迁移页面。

## 8. 迁移策略

采用“新项目先建立统一契约，旧项目保留兼容”的策略：

1. 从 `market-liquidity-profiles` 迁移或重写容量核心，并保留其现有公式和测试语义；
2. 从 `index-research` 迁移微盘重建、年度收益、滚动 CAGR 和回撤计算；
3. 将原项目特有的 CLI 和路径读取改为新项目配置解析；
4. 新项目通过适配器消费 `/home/richard/data/market-data-platform`、`/mnt/data/cold4t` 和 `nira` 数据，不复制原始文件；
5. 每个迁移单元先建立等价测试，再接入统一契约；
6. 旧仓库在新项目完成最小闭环前保持可运行，不做删除性清理。

## 9. 质量、风险和可复现性

报告必须区分以下状态：`verified`、`derived`、`incomplete`、`not_comparable`。

必须检查：

- `(market, symbol, date)` 唯一性；
- 日期范围和市场交易日历；
- 成交额、市值和汇率的单位；
- 缺失、停牌、零成交和过滤数量；
- 当前 Active universe 导致的幸存者偏差；
- ADV 是否使用了未来信息；
- 价格指数、全收益指数和 ETF 代理是否被混用；
- 机械容量是否被误读为策略容量。

所有研究输出必须记录输入路径、快照日期、过滤条件、汇率方法、代码版本和运行命令。

## 10. 验收标准

第一阶段被视为完成，需要满足：

1. `market-research` 可以在没有原始数据写入仓库的情况下运行；
2. 四个市场都能生成统一字段的面板或明确的 `incomplete` 报告；
3. 同一输入重复运行能得到稳定的字段、排序和摘要结果；
4. A股微盘收益与现有 `index-research` 结果在同一口径下能够回归验证；
5. 容量结果使用滞后流动性特征，并明确不是策略实际容量；
6. 日股数据能够从 `nira` 目录读取，并且 JPY 单位与交易日范围有审计信息；
7. 现有两个旧项目的测试和工作树不被破坏；
8. 文档给出一条从原始数据到跨市场报告的完整命令。

## 11. 方案取舍结论

不选择把全部代码塞进 `index-research`，因为它会同时承担指数、市场数据、容量和跨市场报告，边界会迅速失控。

不选择把全部代码塞进 `market-liquidity-profiles`，因为它的核心模型是流动性与容量，而微盘指数收益、指数规则和研究展示属于不同的研究域。

选择新的 `market-research`，是为了让它成为统一研究入口，同时保留两个旧项目作为来源和兼容层。新项目的核心抽象是“带来源元数据的统一市场面板”，而不是某一个市场或某一种指数。
