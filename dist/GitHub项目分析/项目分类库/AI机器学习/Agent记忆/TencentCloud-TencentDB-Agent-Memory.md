# TencentCloud/TencentDB-Agent-Memory

> AI Agent 的团队级记忆中枢——把对话、文档、代码变成可治理、可共享的记忆资产

## 基本信息
- **仓库链接**：https://github.com/TencentCloud/TencentDB-Agent-Memory
- **主语言**：TypeScript
- **Star**：总计 16,272 | 今日新增 +1,053
- **首次上榜**：2026-08-02
- **最近上榜**：2026-08-07
- **累计上榜**：4 次

## 知识归类
A-AI/机器学习 › Agent记忆 › 团队记忆中枢

## 详细介绍
腾讯云出品的 Agent 记忆系统，核心架构基于两大支柱：记忆分层（Memory Layering）和符号化记忆（Symbolic Memory）。短期记忆用 Mermaid 符号图压缩冗长的工具日志，减少 Token 消耗最高达 61.38%；长期记忆构建语义金字塔：L0 对话 → L1 原子事实 → L2 场景块 → L3 人物画像。与把数据堆进向量数据库的传统方案不同，它强调"渐进式披露"——Agent 只关注顶层结构，需要细节时通过 node_id 下钻到底层原始文本。已适配 OpenClaw 和 Hermes Agent 两大框架，本地零配置即用（SQLite + sqlite-vec 后端）。在 OpenClaw WideSearch 基准上，pass rate 提升 51.52%，PersonaMem 准确率从 48% 提升至 76%。

## 适用领域
AI Agent 开发者、需要给 Agent 加上持久记忆的团队、Agent 基础设施建设者、Hermes/OpenClaw 用户。场景：多会话记忆保留、用户画像建模、长程任务上下文压缩、跨 Agent 记忆共享。

## 背景调研
- **开发团队**：腾讯云（TencentCloud），仓库 ID 1203558071，与 OpenClaw 和 Hermes Agent 生态深度集成
- **融资/商业化**：MIT 开源，腾讯云官方项目，关联腾讯云向量数据库（TCVDB）服务
- **社区热度**：16.3K stars，1.5K forks，提供 Discord 社区，被 Trendshift 收录，文档完整度高（含 3 级参数调优指南）

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-02 | #13 | 10,249 | +342 |
| 2026-08-03 | #10 | 10,923 | +604 |
| 2026-08-06 | #3 | 14,999 | +1,891 |
| 2026-08-07 | #1 | 16,272 | +1,053 |
