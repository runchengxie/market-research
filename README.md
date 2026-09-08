# market-research

跨市场股票研究、流动性、容量和指数复现框架。

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

- A 股：`/home/richard/data/market-data-platform/assets/tushare/a_share`
- 港股：`/mnt/data/cold4t/hk-liquidity`
- 美股：`/mnt/data/cold4t/simfin`
- 日股：`/mnt/data/cold4t/nira/current/guan-japanese-nira/data`

日股适配器目前只读取 `daily/*/equities_bars_daily_*.parquet`，并将 J-Quants 的 `Date`、`Code`、`C`、`Vo` 和 `Va` 映射到统一面板。当前 nira 快照没有配套的日频市值字段，因此日股的市值相关分析会标记为 `incomplete`，直到补充相应数据。

架构和迁移范围见 `docs/superpowers/specs/2026-09-07-market-research-design.md`。首个报告包包括流动性汇总、覆盖率诊断、基于滞后流动性特征的机械容量面板，以及来源元数据。

## 迁移后的命令

```bash
uv run market-research report microcap --config configs/local.toml
uv run market-research report indices --config configs/local.toml
uv run market-research report etf-pairs --config configs/local.toml
uv run market-research report cashflow --config configs/local.toml
uv run market-research report liquidity --config configs/local.toml
uv run market-research validate --config configs/local.toml
```

`microcap` 还会生成旧项目公开快照所需的年度收益、滚动 CAGR、滚动回撤和来源标记文件；`indices` 覆盖指数价格回报和 ETF 复权代理，`etf-pairs` 覆盖指数/ETF 配对、全部比较和流动性代表，`cashflow` 覆盖现金流指数研究。迁移输出的命名兼容旧项目，但生成入口统一为本项目。

## Barra / 风格因子研究

`market-research` 是 Barra/风格因子研究的 canonical 入口。quant 中的历史结果可以通过 `[barra].result_root` 作为 provenance 输入，原始行情和实验缓存仍留在 quant 数据资产目录。

```bash
uv run market-research report barra --config configs/local.toml
```

该命令输出历史 19 因子摘要，以及基于 canonical A 股面板重新计算的市值分位收益和尾部单调性诊断。历史报告原本只有五分位多空结果；十分位/二十分位的纯市值单调性应以新输出为准。

## GitHub Pages

公开页面只使用派生文件，不发布原始行情、机器路径和凭证。运行本地页面：

```bash
cd web
npm ci
npm run snapshot  # 仅在刷新本地派生快照时运行
npm run dev
```

推送到 `main` 后，GitHub Actions 会运行页面测试和构建。启用 GitHub Pages 的 Actions 发布来源后，页面地址为：

<https://runchengxie.github.io/market-research/>
