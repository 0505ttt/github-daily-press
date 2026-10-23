# Dicklesworthstone/destructive_command_guard

> AI 编程 Agent 的安全护栏——拦截危险 git/shell 命令的 Rust 高性能 Hook

## 基本信息
- **仓库链接**：https://github.com/Dicklesworthstone/destructive_command_guard
- **主语言**：Rust
- **Star**：总计 4,741 | 今日新增 +497
- **首次上榜**：2026-07-16
- **最近上榜**：2026-07-16
- **累计上榜**：1 次

## 知识归类
G-安全 › 命令安全 › Agent安全护栏

## 详细介绍
dcg（Destructive Command Guard）是一个用 Rust 编写的高性能安全 Hook，在 AI 编程 Agent 执行命令之前进行拦截，阻止 rm -rf、git push --force、git reset --hard、DROP TABLE 等破坏性操作。支持 Claude Code、Codex CLI、Gemini CLI、GitHub Copilot CLI、Cursor、Hermes Agent、Grok (xAI)、Antigravity 等 10+ 种 AI 编程工具。核心特性包括：命令模式匹配与风险评估、可配置的白名单/黑名单策略、支持自定义规则、一行命令安装（cargo install 或 homebrew）、详细日志记录被拦截的命令。项目强调与同类（如 Claude Code 内置权限系统）的区别是跨工具通用——一个 Hook 保护所有 Agent。

## 适用领域
重度使用 AI 编程 Agent 的开发者、DevOps 工程师；需要防止 AI Agent 意外删除代码或破坏 Git 历史的团队；在 CI/CD 中集成 AI Agent 需要安全护栏的运维团队。

## 背景调研
- **开发团队**：Dicklesworthstone（个人开发者），项目迭代活跃，有 claude、codex、dependabot 等 bot 协作
- **融资/商业化**：MIT 开源许可证，完全免费
- **社区热度**：4.7K+ star，在 LinkedIn、X、YouTube 等平台引发关注。Trendshift 已收录，MCP Market 和 AgentConn 等平台均有评测。被视为 AI Agent 安全领域的必要基础设施

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-07-16 | #5 | 4,741 | +497 |
