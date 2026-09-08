# 市场研究边界与研究资产迁移设计

**日期：** 2026-09-08  
**状态：** 待用户审核  
**范围：** `market-research`、`quant-research`、`quant-platform`、`research-workspace/quant-research`

## 1. 目标

把“市场事实/市场现象”从策略研究代码中明确分离，并迁入 `market-research`：

1. 将 inclusive 18-year style-factor study 的市场研究层迁入 `market-research`；
2. 将 `global_six_market` 作为一个独立的跨市场 ETF proxy allocation study 迁入 `market-research`；
3. 让 `quant-research` 只继续拥有 alpha、signal、IC/decay、模型和策略决策层；
4. 让 `quant-platform` 只继续拥有无研究观点的回测、组合、风险、成本、执行模拟和 artifact contract 能力；
5. 保留来源、许可证、数据血缘和研究状态，避免把原始数据、私有缓存或不明来源实现复制到公开仓库。

## 2. 关键边界

| 研究内容 | 归属 |
|---|---|
| 18 年 size/value/momentum 等因子的长期收益、分位组合、市场现象 | `market-research` |
| 微盘效应、尾部单调性、跨时期/市场稳定性、流动性过滤后的市场证据 | `market-research` |
| 六市场 ETF proxy、固定权重、FX、月度再平衡、分散化和可执行性诊断 | `market-research` |
| IC、decay、预测力、signal ranking、alpha hypothesis、因子选择和策略参数 | `quant-research` |
| 通用回测、portfolio accounting、risk、cost、execution simulation、research contracts | `quant-platform` |
| IBKR contract qualification、raw manifest、数据下载和原始数据资产 | 数据/采集层；不在本次公开迁移中复制 |

同一个 size factor 可以在两个仓库中合法存在，但问题必须不同：

- `market-research`：过去的市场是否存在稳定的小市值溢价，以及它在流动性/成本约束下还剩多少；
- `quant-research`：当前策略是否应使用 size signal，以及如何把它转成 alpha 或组合决策。

## 3. 不迁移的内容

- 不迁移 `quant-research` 的 alpha、strategy、ML、signal validation 和专属组合决策；
- 不把 `quant-platform` 的通用回测/执行引擎复制到 `market-research`；
- 不复制 `D:/data/global-six-market` 或任何原始 Parquet、IBKR 凭证、机器绝对路径和大体量缓存；
- 不复制来源许可证尚未确认的 `portfolio_backtester` style-factor slice；必要算法采用有 provenance 的 clean reimplementation；
- 不把 `global_six_market` 当前约 37 个月、缺少股息/成本校准的结果提升为 production 或 complete total-return 结论；
- 不删除旧研究文件。迁移完成后以 README、目录级 notice 和 compatibility map 标明 canonical location。

## 4. 目标目录

```text
market-research/
├── studies/
│   ├── style_factors_18y/
│   │   ├── README.md
│   │   ├── study.yml
│   │   ├── methodology.md
│   │   └── reports/                 # 仅提交小型、去机器路径的派生结果
│   └── global_six_market/
│       ├── README.md
│       ├── study.yml
│       └── reports/
├── src/market_research/
│   ├── style_portfolios/
│   │   ├── definitions.py
│   │   ├── cross_section.py
│   │   ├── diagnostics.py
│   │   └── provenance.py
│   └── studies/global_six_market/
│       ├── config.py
│       ├── loader.py
│       ├── portfolio.py
│       ├── reporting.py
│       └── run.py
└── tests/
    ├── test_style_portfolios.py
    ├── test_style_factor_study.py
    └── studies/test_global_six_market.py
```

目录名称可以在实现前微调，但不改变上述 ownership。`global_six_market` 的公开名称暂定为 `global_six_market_allocation`，报告中必须继续明确它研究的是 ETF proxies，而不是六个国家市场的完整股票宇宙。

## 5. 设计原则

1. `market-research` 不反向 import `quant-research`；迁移代码通过统一 panel/config/artifact contract 接入。
2. 所有形成日因子值必须只使用形成日可见信息；持有期收益从下一可用交易日开始。
3. 市场、ETF、FX、股息、交易日历和成本都要在输出 metadata 中可追溯。
4. `global_six_market` 的 `exploration`、`production_eligible=false`、`automatic_promotion_allowed=false` 状态保持不变。
5. 研究结果与策略结论分离：公共页面只能展示派生快照和状态，不把诊断指标写成预期收益或实盘能力。

## 6. 依赖关系

```text
market-data assets / acquisition validation
                 │
                 ▼
          market-research studies
                 │
        ┌────────┴────────┐
        ▼                 ▼
  market evidence    quant-research
                    alpha / strategy
        └────────┬────────┘
                 ▼
           quant-platform
       reusable computation contracts
```

第一版尽量不改 `quant-platform` 的运行代码；只补充 ownership 文档和必要的通用 contract 接口。若发现确实需要新增通用能力，单独建 PR，不能借迁移之名把 study-specific policy 放进 platform。

## 7. 验收定义

- 两个 study 都能在没有仓库内原始数据的情况下用 fixture 或外部配置运行；
- `market-research` 能生成可审计的研究摘要、状态和 provenance；
- style-factor 研究可输出分位收益、尾部 spread、相邻单调性、覆盖区间和过滤统计；
- global six market 可验证本地月末、下一可用交易日、FX 转 USD、股息缺失状态、成本和 paper-shadow ledger；
- 所有失败门禁都有测试；不满足股息/成本/历史长度/资格条件时仍为 `exploration`；
- `quant-research` 和 `quant-platform` 的 README/迁移 notice 明确 canonical location 与保留边界；
- full test、web test/build、静态检查和 git diff 审查通过；
- 每个仓库经独立 PR 合并 main 后，删除对应 branch/worktree。
