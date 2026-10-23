# strands-agents/harness-sdk

> AWS 开源的 AI Agent SDK（Python + TypeScript），几行代码构建生产级 Agent，无需托管控制面

## 基本信息
- **仓库链接**：https://github.com/strands-agents/harness-sdk
- **主语言**：Python
- **Star**：总计 7,818 | 今日新增 +96
- **首次上榜**：2026-09-24
- **最近上榜**：2026-09-24
- **累计上榜**：1 次

## 知识归类
A-AI/机器学习 › Agent框架 › Agent SDK

## 详细介绍
Strands Agents 是 AWS 开源（Apache 协议）的 Agent SDK，采取 model-driven 路线：你描述目标，模型驱动整个循环，几行代码就能建 Agent，且直接跑在你自己的进程里、没有托管控制面。它把"手写 agent loop 长大后必然要补的东西"一次性打包：生命周期控制（轮次上限、token 预算、取消、停止原因）、工具与结构化输出、MCP 支持、多 Agent 协作模式、记忆与会话管理、模型可移植（Bedrock/Anthropic/OpenAI/Gemini/Ollama 等一键切换）、流式、护栏、tracing 和 evals。本 monorepo 新增了 harness 层：`create_harness()` 一个导入得到预组装、经基准调优的完整 harness（含默认工具、上下文管理、会话、记忆、hooks 和调好的系统提示词），也可以用底层 SDK 从零自建。官网强调"默认可观测"：agent loop 每步决策自动留痕，hooks 可拦截任意步骤做日志、校验或改道。

## 适用领域
要在生产环境跑 AI Agent 的后端/平台工程师（尤其 AWS 生态用户）；适合从对话助手到自主工作流的各类 Agent 场景；解决自研 agent loop 反复造轮子、缺观测缺护栏的问题。

## 背景调研
- **开发团队**：AWS（Amazon 内部生产系统孵化出的开源项目，官网自述"Built from production systems inside Amazon"）
- **融资/商业化**：无独立融资，Apache-2.0 开源，托管方为 AWS/strands-agents 组织
- **社区热度**：官网口径 6,700+ star（当前 7,818 且持续上涨），有 Jit 等公司公开采用案例做基础设施漂移检测 Agent
