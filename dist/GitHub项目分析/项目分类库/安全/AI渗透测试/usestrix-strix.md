# usestrix/strix

> 开源 AI 渗透测试工具——自主 AI「黑客」替你找漏洞、写 PoC、出补丁

## 基本信息
- **仓库链接**：https://github.com/usestrix/strix
- **主语言**：Python
- **Star**：总计 54,084 | 今日新增 +656
- **首次上榜**：2026-08-17
- **最近上榜**：2026-08-18
- **累计上榜**：2 次

## 知识归类
G-安全 › AI渗透测试 › 自主攻击Agent

## 详细介绍
Strix 是一组自主的 AI 渗透测试智能体，像真实黑客一样动态运行你的代码、寻找漏洞并用实际可用的 PoC（概念验证 exploit）加以证实，杜绝静态扫描器常见的误报。开箱即用覆盖侦察、利用、验证全流程，支持多 Agent 协作编排；每个发现都附带复现步骤和修复建议，可一键生成合规级渗透测试报告。CLI 一行命令 `strix --target ./app` 即可发起扫描（需本地 Docker 沙箱 + 任意主流 LLM API Key），也已无缝集成 GitHub Actions，在每个 PR 上自动拦截不安全代码。与 XBOW 等商业产品相比它是 Apache-2.0 完全开源，还提供 `npx skills add usestrix/strix` 让 Claude Code、Cursor 等编程 Agent 直接具备安全测试能力。

## 适用领域
应用安全工程师做快速渗透测试、开发团队在 CI/CD 中前置安全卡点、漏洞赏金猎人自动化信息收集与 PoC 生成、DevSecOps 团队替代昂贵的人工 pentest。

## 背景调研
- **开发团队**：Strix（usestrix 组织，GitHub 组织创建于 2024 年 11 月），官网 strix.ai，主打「open-source AI hackers」；商业侧运营 app.strix.ai 全栈渗透测试平台（免费注册、连仓库即可发起 pentest）
- **融资/商业化**：Apache-2.0 开源 + SaaS 平台（Strix Platform）双轨模式；2026 年 3 月与代理工具 Caido 达成合作，2026 年 4 月上线「每个 PR 渗透测试」能力
- **社区热度**：53K stars、5.7K forks；2025 年 8 月首次以「输入域名，我的开源 Agent 会去黑它」登上 Hacker News，此后多次 Show HN；第三方评测显示其跑过 18 个 LLM 模型的横向对比，社区讨论集中在 AI 红队方向

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-17 | #2 | 53,352 | +781 |
| 2026-08-18 | #2 | 54,084 | +656 |
