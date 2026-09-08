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
