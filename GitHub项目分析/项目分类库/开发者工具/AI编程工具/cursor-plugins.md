# cursor/plugins

> Cursor 官方插件仓库——插件规范 + 官方/第三方插件市场，覆盖开发工具与 SaaS 集成

## 基本信息
- **仓库链接**：https://github.com/cursor/plugins
- **主语言**：TypeScript
- **Star**：总计 12,751 | 本周新增 +1,717
- **首次上榜**：2026-08-15
- **最近上榜**：2026-10-19
- **累计上榜**：8 次

## 知识归类
B-开发者工具 › AI编程工具 › 编辑器插件生态

## 详细介绍
这是 Cursor 官方的插件仓库，定义了 Cursor 插件规范（plugin specification）并提供官方插件。每个插件是仓库根目录下的独立目录，带自己的 `.cursor-plugin/plugin.json` 清单，根目录的 `marketplace.json` 汇总所有插件构成多插件市场。插件结构包含 Agent 技能（SKILL.md）、Cursor 规则（.mdc）、MCP 服务器定义等层。官方插件覆盖开发者工具场景：Continual Learning（AGENTS.md 增量记忆更新）、Cursor Team Kit（团队 CI/代码审查工作流）、Thermos（深度安全/正确性审计）、Orchestrate（并行云 Agent 任务分发）、PR Review Canvas（PR diff 可视化画布）等；第三方集成插件通过官方远程 MCP 服务器接入 Gmail、Google Drive、Salesforce、HubSpot、Gong、X 等 10+ SaaS 产品。

## 适用领域
Cursor 用户（想扩展 Agent 能力的开发者）、想为 Cursor 开发插件的第三方作者、需要在 Cursor 内直接操作 SaaS 工具（邮件/CRM/日历）的团队、研究 Agent 插件规范设计的工程师。

## 背景调研
- **开发团队**：Cursor 官方（Anysphere），仓库创建于 2026 年 1 月，第三方插件作者包括 Lauren Tan（pstack）等
- **融资/商业化**：MIT 开源协议；Cursor 本身是商业产品（Anysphere），此仓库为其插件生态的官方规范载体
- **社区热度**：2.8K stars、227 forks，作为 Cursor 刚开放的插件生态入口，关注度高；插件体系融合 Skills + Rules + MCP 三层能力，是编辑器 Agent 化的代表性设计

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-15 | #11 | 2,800 | +69 |
| 2026-08-16 | #3 | 2,941 | +152 |
| 2026-08-21 | #5 | 4,037 | +473 |
| 2026-08-22 | #9 | 4,409 | +388 |
| 2026-08-29 | #9 | 5,960 | +246 |
| 2026-10-02 | #6 | 9,305 | +157 |
| 2026-10-17 | #9 | 11,941 | +278 |
| 2026-10-19 | #4 | 12,661 | +351 |
| 2026-10-19 | W#9 | 12,751 | +1,717 |
