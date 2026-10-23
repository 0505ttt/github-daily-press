# NVIDIA-NeMo/Switchyard

> NVIDIA 出品的 LLM 流量代理——让 Claude Code / Codex 无缝对接开源模型

## 基本信息
- **仓库链接**：https://github.com/NVIDIA-NeMo/Switchyard
- **主语言**：Rust / Python
- **Star**：总计 1,182 | 今日新增 +408
- **首次上榜**：2026-08-13
- **最近上榜**：2026-08-14
- **累计上榜**：2 次

## 知识归类
B-开发者工具 › AI网关 › LLM流量代理

## 详细介绍
Switchyard 是 NVIDIA NeMo 团队推出的 Rust 代理和库，专为 LLM 流量路由设计。核心能力是协议翻译：在 OpenAI Chat、Anthropic Messages 和 OpenAI Responses 三种 API 格式之间自动转换，让 Claude Code 或 Codex 等编程 Agent 继续说它们的"母语 API"，而后端实际由 vLLM、NVIDIA NIM、Ollama 或任何 OpenAI 兼容端点提供服务。支持多后端路由（随机路由、LLM 分类器路由、信号驱动的阶段路由器、自定义算法）、Prometheus 运维指标（请求、错误、延迟、token 用量、路由开销全覆盖）。一条命令即可启动：switchyard launch claude --model switchyard。目前处于 pre-alpha 阶段。

## 适用领域
使用 Claude Code / Codex 但想接入开源模型的开发者、需要 LLM 流量路由和 A/B 基准测试的工程团队、NVIDIA NIM / vLLM 用户。

## 背景调研
- **开发团队**：NVIDIA NeMo 团队（NVIDIA 官方组织），核心贡献者包括 nachiketb-nvidia、elyasmnvidian、grahamking、ayushag-nv、ryan-lempka 等
- **融资/商业化**：Apache 2.0 开源协议，NVIDIA 官方维护，项目处于 pre-alpha 快速演进阶段
- **社区热度**：783 stars，81 forks，216 commits，38 Issues，51 PRs，Discussions 社区已开放，作为 NVIDIA 官方项目受关注度高

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-13 | #7 | 783 | +370 |
| 2026-08-14 | #10 | 1,182 | +408 |
