# AlexsJones/llmfit

> 一条命令找出你的硬件能跑哪些 LLM——本地模型选型终端利器

## 基本信息
- **仓库链接**：https://github.com/AlexsJones/llmfit
- **主语言**：Rust
- **Star**：总计 35,670 | 今日新增 +247
- **首次上榜**：2026-08-18
- **最近上榜**：2026-09-11
- **累计上榜**：2 次

## 知识归类
B-开发者工具 › 本地LLM工具 › 硬件选型推荐

## 详细介绍
llmfit 是 Rust 编写的终端工具，自动检测你的 RAM、CPU、GPU，对数百个模型与提供方按质量、速度、适配度、上下文四个维度打分，告诉你哪些模型在你的机器上「真的能跑好」。支持多 GPU、MoE 架构、动态量化选择与速度估算，并对接 Ollama、llama.cpp、MLX、Docker Model Runner、LM Studio 等本地运行时。默认交互式 TUI，也有经典 CLI 模式；1.0 版本引入「基准测试与分享」机制：在本机实测 tok/s 后可直接从 TUI 提 PR 回馈项目，同款硬件的用户就能看到带 ✓ 的实测数据而非估算值。安装覆盖 scoop/Homebrew/MacPorts/uv/Docker 全平台。与 HuggingFace 按显存筛模型相比，它更进一步给出「能不能跑好」的综合评分。

## 适用领域
本地 LLM 玩家选型（16GB 内存该跑哪个量化版本）、企业为员工电脑批量推荐可离线运行的模型、评测社区共建硬件-模型适配数据库。

## 背景调研
- **开发团队**：AlexsJones（个人开发者，同时维护 sympozium/llmserve/llama-panel 等姐妹项目），2026 年 2 月创建，半年 32K stars
- **融资/商业化**：无融资，MIT 开源；有官网 llmfit.org 与 Mintlify 文档站
- **社区热度**：32.2K stars；Reddit r/LocalLLaMA 有热帖（497 models / 133 providers 数据点被广泛引用），terminaltrove、hongkiat 等媒体收录推荐，YouTube 有专门演示视频；1.0「数字可验证」版本发布后讨论度持续走高

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-18 | #6 | 32,220 | +239 |
| 2026-09-11 | #6 | 35,670 | +247 |
