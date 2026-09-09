# 现金流与微盘指数探索

本专题是市场证据，不是飞书选股或实盘策略。数据只读共享资产；本地 receipt 保存输入 SHA256，公开页面不包含机器路径、凭证或供应商原始文件。

## 已落地

- index-study 命令：覆盖审计、同组共同窗口、价格收益/CAGR/最大回撤、本地 HTML 笔记。
- 不把800全收益版本和国证价格版本混在一个收益排名中。
- 相同代码日期出现冲突报价则报错；内部缺报价则不计算该组收益。
- 对照外部上交所交易日历，所有指数同时漏掉的交易日也会阻断；未提供日历时不输出表现比较。
- 阻断原因写入HTML和receipt；失败重跑也重写空的schema明确的净值文件，不残留旧净值。
- 微盘 pandas 和 DuckDB 回放：已选持仓缺次日报价时保留缺口，禁止归一化到剩余股票；不允许用缺口生成完整净值。

## 仍未完成，不能解释为复制成功

- 800和国证原有研究实现及结果仍在私有 quant-research，不能未经审查复制到公开仓库。这里只复用公开行情；迁移算法需先审查私有依赖并建立单一维护者。
- A500/1000目前为官方行情对照，尚未完成各期本地选股和持仓追踪回放。
- A500的方案有每次样本数量调整比例一般不超过30%的条件，不可只替换800股票池。
- 微盘缺口处理是 fail-closed，不是完整停牌估值、退市损失和公司行为账本；旧400股净值必须重审。
- 需要验证历史ST、上市资格和形成时点；不得将 next_day_valid 等未来报价可用性用作形成日筛选条件。
- 中证2000/国证2000是小盘对照，不等于最小400股。Wind/同花顺的历史成分与收益口径需要独立验证。
- 400股日频指数与3股周频策略是两个实验，后者留在 quant-research。

## 后续复制验收

先R0官方成分/权重验证收益引擎，再R1本地FCF权重、R2本地成分。
对账包含 overlap、recall、Jaccard、active share、日/月相关性、年化跟踪误差及缺报价计数。
价格/税前全收益、零成本/成本后分别出表；PIT修订链不安全时保持研究标记。

规则来源：

- [A500方案](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931082_Index_Methodology_cn.pdf)
- [1000事实表](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/932369factsheet.pdf)
- [国证方案](https://www.cnindex.com.cn/docs/gz_980092.pdf)
- [同花顺行情接口](https://tushare.pro/document/2?doc_id=260)
