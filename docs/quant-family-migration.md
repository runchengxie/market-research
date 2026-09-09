# Quant 家族归组

仓库目标名称 quant-market-research，保留 package/CLI 兼容名称。
共享原始数据目录不变；新专题默认把结果写在共享数据根的 research/quant-market-research 下。

2026-09-09旧主检出有三个其他任务的 linked worktree，因此新路径先作为同仓库的功能 worktree，未直接搬走主检出。
这些任务结束后再协调移动主检出并执行 git worktree repair；不要删除其他任务分支或工作树。
旧路径下的虚拟环境、定时任务和其他仓库引用保持有效；这次没有切换生产任务。

GitHub重命名保留独立公开仓库，更新origin与页面源码仓库链接。
Pages使用相对base；改名后的站点需要一次正常main构建，旧项目Pages地址不保证重定向。
本次不复制私有quant-research源代码到公开仓库、不自动发布新研究结果。
