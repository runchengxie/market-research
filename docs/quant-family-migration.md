# Quant 家族归组

仓库目标名称 quant-market-research，保留 package/CLI 兼容名称。
共享原始数据目录不变；新专题默认把结果写在共享数据根的 research/quant-market-research 下。

2026-09-09旧主检出有三个其他任务的 linked worktree，因此实施期间新路径先作为同仓库的功能 worktree。
收尾顺序：PR合并并验证后，清理本任务worktree，移动主检出到新路径，再保留旧路径兼容符号链接。
已有其他任务的worktree注册路径通过旧路径链接继续有效，不删除或重置其他任务的分支、文件或Git状态。
不能直接删除旧路径链接：先检查其他worktree、虚拟环境、定时任务及跨仓路径引用，再另做清理迁移。
本次不切换生产任务；数据路径保持不变。

GitHub重命名保留独立公开仓库，更新origin与页面源码仓库链接。
Pages使用相对base；改名后的站点需要一次正常main构建，旧项目Pages地址不保证重定向。
本次不复制私有quant-research源代码到公开仓库、不自动发布新研究结果。
