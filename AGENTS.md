# quant-market-research 工作规则

本项目是 Quant 家族的可执行、可视化市场研究笔记，保留独立公开仓库。
共享原始数据由 quant-market-data-platform 管理；通用回测与执行模拟复用 quant-platform；
私有 alpha、模型与飞书选股留在 quant-research。不得复制供应商原始数据、凭证或私有策略到本仓库。
研究输出写仓库外，页面只接收经审查的派生结果；未知数据和未通过审计的收益不得标为已验证。

## 多 agent 开发流程（强制）

1. 只读检查 git status、worktree list 和当前分支；识别其他任务的改动，不覆盖、不清理。
2. git fetch origin 后从 origin/main 为每个任务创建独立功能分支及仓库外 worktree，建议放在 /home/richard/code/.worktrees/<repo>-<topic>。
3. 每个 agent 独占 worktree 和分支。代码、测试、文档都在任务 worktree 中修改，不在共享 main 上开发。
4. 完成匹配范围的本地验证，提交并推送功能分支，开目标为 main 的 PR。禁止绕过 hooks 或检查。
5. 检查 PR review、必需检查和冲突；通过后合并 main，不直推 main、不强推抢合并。
6. 确认远端 PR 已合并、变更已进入 main 且任务 worktree 没有唯一未保存内容；删除远端任务分支，移除本任务 worktree，再删除本地任务分支。已检出的分支不能先删除。
7. 主检出干净时才允许 fast-forward 同步 main。记录 PR URL、合并 SHA、验证结果与遗留事项。

不能清理其他 agent 的分支或 worktree；未合并不得删除唯一改动；不得用 --force、reset --hard 或跳过检查掩盖问题。
同仓 worktree 共享 hooks 配置，不在任务 worktree 中修改全仓 hooks。
生产定时任务使用稳定发布路径，数据、日志和缓存不能依赖待删除的任务 worktree。

## 验证

```bash
uv run --extra duckdb --with pytest pytest -q
git diff --check
cd web
npm ci
npm test
npm run build
```

按改动范围执行。文档改动检查路径、命令与现状；算法改动先补回归测试。
指数表现比较和本地成分复刻必须分开标注；形成时点不得使用未来报价或今天的证券资格。
