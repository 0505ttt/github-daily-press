# pacifio/atlas

> 给编码 Agent 用的版本控制系统：每个 commit 都能追溯到「哪个 Agent 为什么改的」

## 基本信息
- **仓库链接**：https://github.com/pacifio/atlas
- **主语言**：Rust
- **Star**：总计 2,830 | 今日新增 +895
- **首次上榜**：2026-09-16
- **最近上榜**：2026-09-16
- **累计上榜**：2 次

## 知识归类
B-开发者工具 › Agent工作空间 › Agent版本控制

## 详细介绍
定位是「Agent 时代的 source control」：每次 Agent 运行都产生 checkpoint，commit 被关联回产生它的会话——提示词、工具调用、推理过程、文件变更全部绑在一起，几个月后仍然可以查询「哪个 Agent 在哪个 prompt 下改了这行代码」。Claude Code、Codex、Atlas 内置 Agent 以及 ACP 注册表里的任意 Agent 可以并排跑同一个代码库，共享一份记忆：Claude Code 做过的决定会自动出现在 Codex 的下一个 prompt 里，中途换 Agent 不用从头再来。你的 Markdown 笔记（.atlas/knowledge/、CLAUDE.md、AGENTS.md）会作为上下文喂给所有 Agent；@ 符号可以把文件、目录、符号、分支、commit、论文、历史会话直接解析进 prompt。本地优先（代码、笔记、会话留在本机），Tauri 构建，目前官方支持 macOS。

## 适用领域
同时使用多个编码 Agent 的开发者；需要审计 Agent 改动历史的工程管理者；Agent 编排与协作方向的探索者。

## 背景调研
- **开发团队**：pacifio 团队，官网 tryatlas.cc，有 Discord 社区，2026 年 9 月 3 日左右上过 Trending
- **融资/商业化**：MIT 开源（本地免费），团队版提供云端同步与组织管理
- **社区热度**：4.5K star，Trendshift 双徽章（仓库+Rust 语言日榜），Instagram/Twitter 有自媒体自发传播

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-09-03 | #9 | 2,830 | +895 |
