# cloudflare/security-audit-skill

> Cloudflare 出品的编程 Agent 安全审计技能：六阶段流水线 + 对抗式验证，把你的 Agent 变成安全审计员

## 基本信息
- **仓库链接**：https://github.com/cloudflare/security-audit-skill
- **主语言**：JavaScript
- **Star**：总计 45,355 | 今日新增 +2,264
- **首次上榜**：2026-09-18
- **最近上榜**：2026-10-25
- **累计上榜**：10 次

## 知识归类
G-安全 › AI安全审计 › Agent化漏洞挖掘技能

## 详细介绍
这是一个 coding-agent skill（npx skills add 一行装进 Claude Code 等编程 Agent），源自 Cloudflare 官方博客《Build your own vulnerability harness》中漏洞挖掘 harness 的单仓库起点。它编排多个隔离 Agent 走六阶段审计流水线：侦察（并行研究 Agent 映射架构、信任边界与输入面）→ 狩猎（多个通用 Agent 按攻击类并行进攻：注入/访问控制/业务逻辑/密码学/链式攻击，可再派子 Agent 深挖）→ 验证（专门的独立 Agent 反过来试图推翻每条发现，对抗式杀死误报）→ 报告（人类可读 REPORT.md）→ 结构化输出（符合 report-schema.json 的 findings.json，附带零依赖校验脚本）→ 独立复核（全新 Agent 逐条核对事实声明）。对同一仓库多次运行是叠加式的：会读取历史 findings.json 跳过已知问题、专攻未覆盖路径。核心区别于普通 AI 审计工具的地方：对抗验证 + 机器可读输出 + 独立复核三重把关。

## 适用领域
用 Claude Code 等编程 Agent 的开发者做代码库安全自查；企业安全团队搭建自动化审计流水线；研究 Agent 编排（多 Agent 分工/对抗验证范式）的工程师。

## 背景调研
- **开发团队**：Cloudflare，配套博客《Build your own vulnerability harness》（2026-06-18，作者 Dan Jones、Alexandra Godoi、Grant Bourzikas）
- **融资/商业化**：开源（Cloudflare 官方仓库），是其内部漏洞挖掘 harness 演化出的公开起点版，初始 skill 约 450 行
- **社区热度**：上线即登 Trending #2（+1,249/日）；社区已有 daedalus/ai-vuln-harness 等项目按此思路扩展出 17 阶段管线与 FAISS 语义去重；README 还内置 AI/LLM 注入、Web 协议认证、客户端、内存安全四大领域的专门攻击类手册

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-09-18 | #2 | 10,435 | +3,606 |
| 2026-09-19 | #1 | 13,984 | +3,006 |
| 2026-09-20 | #1 | 16,087 | +3,162 |
| 2026-09-21 | #3 | 18,082 | +2,428 |
| 2026-10-21 | #2 | 34,275 | +1,712 |
| 2026-10-22 | #1 | 36,597 | +2,012 |
| 2026-10-23 | #4 | 39,578 | +2,979 |
| 2026-10-24 | #1 | 42,455 | +2,716 |
| 2026-10-25 | #1 | 45,355 | +2,264 |
