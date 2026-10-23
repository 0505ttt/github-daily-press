# thedotmack/claude-mem

> 给所有 AI Agent 的跨会话持久记忆系统——捕获、压缩、按需注入历史上下文

## 基本信息
- **仓库链接**：https://github.com/thedotmack/claude-mem
- **主语言**：TypeScript
- **Star**：总计 98,418 | 今日新增 +662
- **首次上榜**：2026-10-06
- **最近上榜**：2026-10-09
- **累计上榜**：5 次

## 知识归类
A-AI/机器学习 › Agent记忆 › 跨会话持久记忆

## 详细介绍
claude-mem 解决的是"Agent 每次开新会话都失忆"的问题：它自动捕获会话中的工具调用观察记录，用 AI 生成语义摘要并压缩存储，之后在新会话中按需注入相关上下文，让 Agent 对项目保持连续认知。技术上基于 Claude Agent SDK 构建，提供渐进式披露（分层记忆检索 + token 成本可见）、mem-search 技能搜索、Web 实时记忆流查看器等能力；最初为 Claude Code 设计，现已支持 Claude Code、OpenClaw、Codex、Gemini、Hermes、Copilot、OpenCode 等几乎所有主流编程 Agent，还有 OpenClaw 网关一键安装脚本。安装走 `npx claude-mem install` 或 Claude Code 插件市场，npm 全局安装只装 SDK 不注册钩子。商业版 CMEM Pro 提供托管记忆服务（14-30 天免费试用）。

## 适用领域
天天和 AI 编程助手打交道的开发者；长周期项目需要 Agent 记住"上次改到哪、为什么这么改"的团队；多 Agent 工作流中希望共享项目记忆的用户。

## 背景调研
- **开发团队**：Alex Newman（@thedotmack），基于 Claude Agent SDK 构建
- **融资/商业化**：Apache-2.0 开源 + CMEM Pro 托管记忆订阅（官方 X 账号 @Claude_Memory，Discord 社区）
- **社区热度**：GitHub 95K+ star、8.4K fork，npm 周下载 12,674，入选 Awesome Claude Code，版本迭代极快（13.28.0，4小时前更新）

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-10-04 | #8 | 95,571 | +79 |
| 2026-10-06 | #6 | 96,956 | +536 |
| 2026-10-07 | #6 | 97,123 | +536 |
| 2026-10-08 | #8 | 97,670 | +578 |
| 2026-10-09 | #5 | 98,418 | +662 |
