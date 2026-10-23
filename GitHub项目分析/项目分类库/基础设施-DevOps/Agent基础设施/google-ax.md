# google/ax

> 今日最大黑马：Google 的 Agent 版 Kubernetes，一个 YAML 把智能体编排到亿级

## 基本信息
- **仓库链接**：https://github.com/google/ax
- **主语言**：Go
- **Star**：总计 10,269 | 今日新增 +1,376
- **首次上榜**：2026-09-23
- **最近上榜**：2026-09-25
- **累计上榜**：3 次

## 知识归类
E-基础设施/DevOps › Agent基础设施 › 智能体编排

## 详细介绍
Google 开源的声明式 Agent 编排运行时，今日 +2,305 stars 是榜单第一增速。口号是「声明一个 Agent 任务，AX 负责沙箱化、装工作区、锁网络、扩到集群规模」，官方直接类比：用过 Kubernetes 的话 ax 会很熟悉。四个原语覆盖 Agent 运维全链路：Task（沙箱内跑不可信代码，CPU/内存限额）、Workspace（预装 Git 仓库/MCP Server/技能包，Agent 冷启动即热）、Gateway（出站流量锁到显式白名单——Agent 乱花钱的主要防线）、Model（平台自身用哪个 LLM，凭据走 K8s Secret）。体验上 ax apply/watch/ssh/suspend/resume 全套 kubectl 风格命令，可随时 ssh 进沙箱「看 Agent 在干嘛」。跑在 Agent Substrate（榜单第 2 名）之上，两者构成 Google 的 Agentic Infrastructure 组合拳。

## 适用领域
AI 平台团队大规模运行自主编码/工作流 Agent；企业安全团队需要给 Agent 上网络围栏与审计；熟悉 K8s 想转 AI Infra 的后端工程师的上手首选

## 背景调研
- **开发团队**：Google（官方仓库），Google Cloud 博客以「Agent Executor, Google's distributed Agent Runtime」专文官宣
- **核心贡献者**：Jaana Dogan（rakyll，Google 著名工程师）在 X 上推广，定位「通用运行时：动态调度、断点恢复、自动纠错、审计、轨迹管理」
- **生态**：与 agent-substrate/substrate 组成「Agentic Infrastructure」组合；媒体报道称其解决「Agent 跑 4 小时崩掉」的长时任务痛点
- **项目状态**：API 未稳定，官方警告将有破坏性变更

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-09-23 | #5 | 8,195 | +2,305 |
| 2026-09-24 | #2 | 8,972 | +1,542 |
| 2026-09-25 | #4 | 10,269 | +1,376 |
