# Barra 研究迁移记录

## Canonical ownership

`market-research` 现在是跨市场 Barra/风格因子研究的 canonical 入口。`quant` 继续承担行情资产、回测运行、notebook 和历史实验产物，不再承担这类能力的唯一入口。

## Migrated source

本次接入的历史结果目录为：

`/home/richard/data/quant/market-data-platform/strategy_outputs/style-factors/weekly-20260904`

该结果包包含 19 个因子：beta、chip concentration、dividend yield、earnings yield、fund breadth/ownership、growth、institution holding、leverage、liquidity、liquidity flow、lowvol、momentum、ps value、quality、size 和 value。

## New canonical capability

`market-research report barra` 读取历史 manifest/meta/factor summary，并对 canonical A 股面板执行市值因子分位分析。Q1 表示最小市值组，输出未来持有期收益、尾部价差、分位排序诊断和覆盖信息。该结果属于历史描述性证据；形成日数量存在时间相关性，不应直接当作独立样本或统计显著性检验。

## Known boundary

原历史报告使用月末五分位“大市值减小市值”多空口径，但没有保存纯市值十分位/二十分位曲线。因此历史摘要仅作为 provenance，分位排序诊断以新命令生成的 `barra_size_quantiles.csv` 为准；任何正式显著性结论仍需独立的统计检验设计。

## 网页收益口径（2026-09-09 核对）

核对历史包 `style-factors/weekly-20260904` 的 `meta.json`、
`style_analysis_report.md`，以及生成端 `style_factors/workflow.py` 和
`portfolio_backtester/style_factors_backtest.py` 后，网页按以下口径标注：

- 每月末按因子得分分五组，两端初始等权、固定份额持有。日序列为最高分组收益减最低分组收益；市值因子方向为大市值减小市值。
- 总览的 `geometric_annual_ret` 来自 `product(1 + daily_spread) ** (252 / observations) - 1`；逐年 `annual_ret` 来自当年 `product(1 + daily_spread) - 1`，不是全年外推值。源文件以百分数记录，网页仍除以 100 后交给百分比格式化函数。
- 年化、年度收益、波动、Sharpe、回撤和胜率均描述历史多空合成序列；相关性也是多空日收益差之间的相关性。这些数值不是已验证的可实现策略账户回报。
- 历史计算将持仓期缺失收益记为零，退市终值及完整执行限制未验证。逐期券源、借券成本、保证金和资金占用尚未验证，不能由本页判断具体 A 股组合可执行或一概不可执行。
- 风格风险分析还可用于暴露解释和归因，不能把所有 Barra 分析等同于预测性 alpha。IC / rankIC 和分位单调性更直接检验得分与未来收益的关系，但仍需统计与样本外验证；本页未发布 IC / rankIC 数值。
- 原始日行情、日频估值及后续重建财务支撑历史包；按公告日对齐和部分持仓 PIT 处理不证明全部历史财务版本完整 PIT。行业信号去均值也不保证组合行业权重中性。

公开依据为 [历史摘要](../web/public/data/barra/historical_factor_summary.json)、
[年度派生表](../web/public/data/barra/factor_yearly.csv)、
[相关性](../web/public/data/barra/factor_correlation.json) 和
[来源清单](../web/public/data/barra/barra_source_manifest.json)。本次只改展示文字，
不重算或更换派生数据，不复制生成端代码、原始数据或私有研究内容。

档案总览新增 `./research/recovery.html` 入口。该独立公开研究摘要由 recovery 任务生成，
本任务不创建占位报告；合并发布前须由主 agent 确认真实 HTML 已纳入发布目录。

验证时运行 `cd web && npm test && npm run build`，并按 Pages 工作流扫描
`web/dist` 中的本地路径和凭证标记，确认 `git diff -- web/public/data` 为空。
浏览器验收应检查总览入口的可见性和相对地址、Barra 多空合成标签与研究边界、
因子切换后年化值与公开摘要一致，以及市值十分位仍保持独立诊断口径。

本次验证结果：Python 59 项、前端 12 项通过，生产构建成功（保留既有 ECharts
大于 500 kB 的分块提示）；公开边界扫描、`git diff --check` 与公开数据零差异检查通过。
公开摘要、年度表和相关性文件经 `cmp` 与历史包对应文件逐字节一致。
Chromium 实际渲染检查通过：总览链接可见且地址准确，Barra 口径与限制说明可见，
19 个因子逐一切换后的年化值与公开摘要一致，移动端年度标题可见且无页面异常。
未新增功能 helper 或源码字符串断言测试；研究摘要 HTML 的内容和链接落地验收由
recovery 任务完成，不能以 Vite 的单页回退响应代替真实 HTML 验证。
