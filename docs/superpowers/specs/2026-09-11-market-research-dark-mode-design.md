# quant-market-research Dark Mode 设计

## 目标

为 `quant-market-research` 的研究档案页面增加可持久化的暗色主题，同时保留当前暖白 editorial 主题作为默认值。暗色模式应借鉴 `quant-trading-workbench` 的 token 分层和 chart surface 分离，而不是简单反转颜色。

## 交互

- 页面右上角提供 `浅色 / 深色 / 系统` 循环切换按钮，并带有可读的 `aria-label`。
- 用户选择保存到 `localStorage`，key 为 `market-research-theme`。
- `system` 根据 `prefers-color-scheme` 解析，监听系统主题变化。
- 首屏在 React 挂载前根据本地选择设置 `data-theme`，避免明显的闪烁。
- URL hash、研究 tab、数据加载和图表交互不受主题切换影响。

## 视觉 token

将 `styles.css` 中的核心颜色收敛为 CSS variables：paper、surface、surface-strong、ink、muted、rule、accent、callout、chart-surface、chart-grid、chart-axis 和 tooltip。浅色值保持现有页面观感；暗色值使用深灰蓝背景、低对比规则、浅灰文本、降低饱和度的砖红/蓝色。

图表组件从 `MicrocapCharts.tsx` 和 `ResearchCharts.tsx` 消费共享的 CSS variable 颜色，通过 `getComputedStyle(document.documentElement)` 或主题配置读取 axis/grid/tooltip 颜色；业务 series 颜色仍由调用方指定，但默认值必须在暗色背景上可读。

## 非目标

- 不改变研究数据、页面信息架构、报告内容和 URL。
- 不引入 UI 框架或第三方主题库。
- 不把默认主题改成暗色。
- 不要求所有历史颜色语义消失；只迁移影响页面底色、文本、边框、控件和图表可读性的核心颜色。
