# alphaXiv/OpenResearch

> 把编码 Agent 变成科研 Agent：本地优先的自动科研工作台

## 基本信息
- **仓库链接**：https://github.com/alphaXiv/OpenResearch
- **主语言**：Rust
- **Star**：总计 4,904 | 今日新增 +940
- **首次上榜**：2026-09-16
- **最近上榜**：2026-09-18
- **累计上榜**：2 次

## 知识归类
B-开发者工具 › Agent工作空间 › 科研Agent工作台

## 详细介绍
把 Claude Code、Codex、OpenCode 或 Cursor 接进来，让它们做科研：文献综述、提出假设、跑实验、产出论文级 artifact，一条 orx up 命令打开本地仪表盘（Rust + MIT 协议）。核心设计是「每个研究方向一个独立 agent 会话 + 隔离 git worktree」，实验用 git 原生树管理，每次运行都归档其代码 commit 的不可变快照，证据（日志、diff、结果）与产生它的过程绑定在一起。同一份快照可以跑在本地、SSH、Slurm、Kubernetes、Modal 甚至 Tinker 上，无需公开代码仓库；数据全部存本地 SQLite。autoresearch 模式可以让全流程自主循环：提出想法→改代码→跑实验→检查证据→决定下一步，多 Agent 并行探索不同方向。

## 适用领域
想用 AI Agent 做可复现实验、自动化论文复现的科研人员；需要并行探索多个研究方向的实验室；关注 autoresearch（自动科研循环）方向的研究者。

## 背景调研
- **开发团队**：alphaXiv 公司（arXiv 论文开放讨论平台方，总部旧金山，团队分布美英印）
- **融资/商业化**：2025 年 11 月完成 700 万美元种子轮；软件 MIT 开源免费，靠托管计算（compute marketplace）变现；2026-08-24 正式发布
- **社区热度**：2026-06-07 上线 GitHub，9 月初 1,315 star，今日 +593 首上榜；与 Thinking Machines Lab 合作用 Tinker 复现论文（官方博客有 Qwen3.8-27B/GPT-OSS-120B 复现成本对照实验）

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-09-18 | #5 | 4,904 | +940 |
