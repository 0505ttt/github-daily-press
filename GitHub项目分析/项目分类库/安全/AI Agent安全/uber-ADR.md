# uber/ADR

> 企业级 AI Agent 安全系统——可观测性 + 安全基准 + 威胁检测，已在 Uber 生产部署

## 基本信息
- **仓库链接**：https://github.com/uber/ADR
- **主语言**：Python
- **Star**：总计 1,012 | 今日新增 +354
- **首次上榜**：2026-08-06
- **最近上榜**：2026-08-06
- **累计上榜**：1 次

## 知识归类
G-安全 › AI Agent安全 › 企业级检测响应

## 详细介绍
Uber 开源的 ADR（Agentic AI Detection and Response）是企业 AI Agent 的安全防护系统，已在 Uber 生产环境部署，配套论文被 MLSys 2026 接收。它通过四大能力守护 Agent：① 可观测性——在 macOS/Linux/Windows 上捕获 Cursor、Claude Code、Codex 等 7+ 编码工具及客服 Agent 的意图、工具调用与执行轨迹；② ADR-Bench 基准——300+ 任务、133 个 MCP 服务器、覆盖全部 17 种 Agent 攻击手法；③ 双层检测架构——高召回初筛 + 针对可疑会话的深度 Agent 推理；④ 防护组件（未开源）。区别于通用 WAF，它专门针对 Agent 的提示注入、越权工具调用等新型风险。

## 适用领域
企业安全团队、大规模部署 AI 编码/客服 Agent 的组织、需要评估 Agent 攻击面与防护策略的安全工程师、Agent 安全研究者。

## 背景调研
- **开发团队**：Uber 工程团队（Li Chenning、Hu Pan、Xu Justin 等），论文署名包含 Mohammad Alizadeh（MIT）等学术界合作者
- **融资/商业化**：Apache 2.0 开源，源自 Uber 内部生产系统，论文被 MLSys 2026 接收（顶会背书），防护组件闭源
- **社区热度**：1K stars 早期阶段但今日 +354 增长迅猛，是企业 Agent 安全新赛道的重要开源标杆，ADR-Bench 是首个覆盖全部 17 种 Agent 攻击手法的综合基准
