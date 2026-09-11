# 本地运行手册

## 安装

```bash
uv sync --extra dev --extra duckdb
cp configs/local.example.toml configs/local.toml
```

编辑 `configs/local.toml`，让每个数据源指向本机已有的数据目录。该文件已被 Git 忽略，因为其中包含机器相关路径。处理大型 A 股 Parquet 目录时，将 `use_duckdb = true`，并通过 `uv sync --extra duckdb` 安装 DuckDB 依赖。

## 检查数据目录

```bash
uv run market-research validate --config configs/local.toml
```

该命令只检查配置的数据目录是否存在，不会读取全部行情数据。

## 构建流动性报告

```bash
uv run market-research report liquidity --config configs/local.toml
```

结果会写入 `output_root`：

- `liquidity_report.json`
- `liquidity_summary.csv`
- `coverage_diagnostics.csv`

## 构建 A 股微盘重建

```bash
uv run market-research report microcap --config configs/local.toml
```

该结果使用最小市值 400 只股票等权的研究规则，不代表 Wind 官方 `8841431.WI` 指数。计算中没有模拟交易成本、涨跌停成交、停牌成交、市场冲击和策略容量。

## 构建最小市值股票成交额统计

```bash
uv run market-research report smallcap-turnover --config configs/local.toml
```

该报告按每日总市值选取最小的 10、50、100、200、400 和 1000 只 A 股，统计成交额
总和、均值、中位数和分位数。完整的 `smallcap_turnover_daily.csv`、摘要和 manifest
写入配置的仓库外 `output_root`，不会自动进入 Git 或公开页面。

如果需要 2008 年起的扩展版本：

```bash
uv run market-research report smallcap-turnover-history --config configs/local.toml
```

该版本连接 2008 年起的 daily 与 daily_basic，覆盖尽可能长的历史，但由于历史源没有
可靠的 ST 和停牌字段，输出会标记为 `incomplete`，不能与 2015 年后的清洗版本直接混为
同一质量等级。

生成两套口径的重叠期审计：

```bash
uv run market-research report smallcap-turnover-audit --config configs/local.toml
```

该命令比较共同日期和 N 分组下的成交额中位数差异，并输出 5%、10% 和 25% 误差范围
覆盖比例。它用于发现口径变化，不把历史源提升为已验证数据。

## 当前数据目录

- A 股日频清洗数据：`/home/richard/data/quant/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data`
- 港股 RQData：`/mnt/data/cold4t/hk-liquidity/assets/rqdata/hk`
- 美股 SimFin：`/mnt/data/cold4t/simfin/us/extracted/us-shareprices-daily.csv`
- nira 提供的 JPX、J-Quants 数据：`/mnt/data/cold4t/nira/current/guan-japanese-nira/data`
## Barra / 风格因子报告

在 `configs/local.toml` 中配置 A 股数据根目录和可选的历史风格因子结果目录后运行：

```bash
uv run market-research report barra --config configs/local.toml
```

输出包括：

- `barra_summary.json`：历史因子摘要、数据来源和市值单调性指标；
- `barra_size_quantiles.csv`：按形成日和市值升序分位的未来收益；
- `barra_source_manifest.json`：canonical 项目、历史结果和原始数据的 provenance。

市值分位中 Q1 是最小市值组，`monotonicity_score` 是相邻分位收益满足“小市值收益不低于大市值收益”的比例。该指标不等同于显著性检验，仍需结合成本、容量、停牌和幸存者偏差审阅。
