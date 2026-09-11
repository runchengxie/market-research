# quant-market-research

Quant 家族的可执行、可视化研究笔记：跨市场股票、流动性、容量和指数复现。

共享数据由 `quant-market-data-platform` 管理，通用回测与执行能力由
`quant-platform` 提供，私有 alpha 与飞书选股留在 `quant-research`。
本项目保留独立仓库；Python 包 `market_research` 和 CLI `market-research` 保持兼容。
原始数据、缓存和完整运行结果不随代码迁移，不另建数据副本。

## 现金流与微盘研究笔记

```bash
uv run market-research report index-study --study studies/index_replication/study.example.json
```

示例只读共享行情，输出在仓库外；异机先修改示例中的路径。
输出 coverage.csv、comparison.csv、normalized_nav.csv、receipt.json 和本地 report.html。
同时输出回本水下期、买入日等待、固定持有年限亏损比例、recovery.json 和本地 recovery.html。长窗口配置见
`studies/index_replication/recovery.study.json`，详细口径见 `recovery-methodology.md`。
主站首页仅显示研究摘要，回本数据和方法在现金流、小微盘专题内阅读。
两个专题另设指数复刻进展，展示经过复核的派生汇总，价格回报与税前全收益分别比较。
数据来源、固定实验区间和待补证据见 [复刻研究记录](studies/index_replication/replication-progress-20260909.md)。
旧网页 `research/recovery.html` 会跳转到 `#cashflow-recovery`，不要用本地报告覆盖跳转页。
现金流按价格指数统一比较800、国证、A500、1000、全指和500；
微盘纳入同花顺、万得及中证/国证2000对照，缺数据明确标记，不以代理填补。
这是行情证据层，不能把它当作已完成成分复刻。研究进度和阻断项见
`studies/index_replication/README.md`。

新开发路径为 `/home/richard/code/quant/quant-market-research`。
迁移后旧路径保留兼容链接及已有 worktree，避免打断其他在途任务；详见 `docs/quant-family-migration.md`。

本项目统一承接并 supersede `index-research` 与 `market-liquidity-profiles` 的独立发布职责。旧仓库保留历史代码和研究记录；持续维护的代码、公开页面和派生快照集中在这里。本项目是 canonical research entry point，旧仓库仅作为 legacy archive。

项目采用本地优先的方式读取现有行情资产，不把原始数据复制到仓库。当前支持 A 股、港股、美股和日股。

## 本地环境

```bash
uv sync --extra dev --extra duckdb
cp configs/local.example.toml configs/local.toml
uv run market-research --help
uv run market-research config inspect --output-root outputs
```

本地配置包含机器相关路径，已被 Git 忽略。请不要在配置文件中填写凭证。

当前已接入的数据目录包括：

- A 股：`/home/richard/data/quant/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data`
- 港股：`/mnt/data/cold4t/hk-liquidity`
- 美股：`/mnt/data/cold4t/simfin`
- 日股：`/mnt/data/cold4t/nira/current/guan-japanese-nira/data`

日股适配器目前只读取 `daily/*/equities_bars_daily_*.parquet`，并将 J-Quants 的 `Date`、`Code`、`C`、`Vo` 和 `Va` 映射到统一面板。当前 nira 快照没有配套的日频市值字段，因此日股的市值相关分析会标记为 `incomplete`，直到补充相应数据。

架构和迁移范围见 `docs/superpowers/specs/2026-09-07-market-research-design.md`。首个报告包包括流动性汇总、覆盖率诊断、基于滞后流动性特征的机械容量面板，以及来源元数据。
数据保存、Parquet/CSV 分工和公开发布边界见 `docs/data-storage-and-publication.md`。

## 迁移后的命令

```bash
uv run market-research report microcap --config configs/local.toml
uv run market-research report indices --config configs/local.toml
uv run market-research report etf-pairs --config configs/local.toml
uv run market-research report cashflow --config configs/local.toml
uv run market-research report liquidity --config configs/local.toml
uv run market-research report smallcap-turnover --config configs/local.toml
uv run market-research validate --config configs/local.toml
```

`microcap` 还会生成旧项目公开快照所需的年度收益、滚动 CAGR、滚动回撤和来源标记文件；`indices` 覆盖指数价格回报和 ETF 复权代理，`etf-pairs` 覆盖指数/ETF 配对、全部比较和流动性代表，`cashflow` 覆盖现金流指数研究。迁移输出的命名兼容旧项目，但生成入口统一为本项目。

## Barra / 风格因子研究

`market-research` 是 Barra/风格因子研究的 canonical 入口。quant 中的历史结果可以通过 `[barra].result_root` 作为 provenance 输入，原始行情和实验缓存仍留在 quant 数据资产目录。

```bash
uv run market-research report barra --config configs/local.toml
```

该命令输出历史 19 因子摘要，以及基于 canonical A 股面板重新计算的市值分位收益和尾部排序诊断。页面将其标记为历史描述性证据；日频横截面观测存在时间相关性，不自动等同于独立样本、统计显著性或策略有效性。

研究页面以历史研究档案为主线，并区分历史研究、研究中的专题和待补数据。现金流、小微盘、指数/ETF 与 Barra/18 年因子属于历史档案；跨市场小微盘流动性属于研究中的专题；Global Six-Market 和日股同口径分桶属于待补数据与未来研究。完整边界见 `docs/research-information-architecture.md`。

市场证据层的 18 年风格研究和六市场 ETF proxy allocation study 位于
`studies/`；alpha、signal、IC/decay 和策略决策仍属于 `quant-research`，
通用回测与执行模拟仍属于 `quant-platform`。六市场研究保持
`exploration`，不提交订单，也不把 ETF proxy 结果等同于完整国家股票市场。

## GitHub Pages

公开页面只使用派生文件，不发布原始行情、机器路径和凭证。运行本地页面：

```bash
cd web
npm ci
npm run snapshot  # 仅在刷新本地派生快照时运行
npm run dev
```

推送到 `main` 后，GitHub Actions 会运行页面测试和构建。启用 GitHub Pages 的 Actions 发布来源后，页面地址为：

<https://runchengxie.github.io/quant-market-research/>
