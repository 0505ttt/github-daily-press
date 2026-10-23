# MoonshotAI/FlashKDA

> 月之暗面开源的高性能 Kimi Delta Attention CUDA 算子——基于 CUTLASS 实现

## 基本信息
- **仓库链接**：https://github.com/MoonshotAI/FlashKDA
- **主语言**：Cuda
- **Star**：总计 970 | 今日新增 +216
- **首次上榜**：2026-07-30
- **最近上榜**：2026-07-30
- **累计上榜**：1 次

## 知识归类
A-AI/机器学习 › LLM推理优化 › CUDA高性能算子

## 详细介绍
FlashKDA 是月之暗面（Moonshot AI）开源的高性能 Kimi Delta Attention（KDA）前向计算核，基于 NVIDIA CUTLASS 库用 C++ 实现。KDA 是 Kimi Linear 架构的核心注意力机制，FlashKDA 在 NVIDIA H20 GPU 上实现了 1.72×–2.22× 的 prefill 加速。支持可变长度批处理（variable-length batching），可被 flash-linear-attention 库自动调度（无需手动修改代码）。硬件要求 SM90+（H100/H200/H20 等架构）、CUDA 12.9+、PyTorch 2.4+。提供了完整的 Kernel API 和与 flash-linear-attention 的集成路径。对于部署 Kimi Linear 模型的团队来说，这是一个即插即用的推理加速方案。与 Triton 实现相比，CUTLASS C++ 实现能更精细地控制 GPU 内存层级和计算调度。

## 适用领域
LLM 推理引擎开发者、部署 Kimi Linear 模型的团队、GPU 算子优化工程师、线性注意力机制研究者；拥有 H100/H200/H20 等 SM90+ 架构 GPU 的 AI 基础设施团队。

## 背景调研
- **开发团队**：月之暗面（Moonshot AI / Kimi），中国头部大模型公司，核心贡献者包括 esp0r、gau-nernst 等
- **融资/商业化**：MIT 开源，月之暗面已获多轮大额融资（估值超 30 亿美元），FlashKDA 是其开源生态布局的一部分
- **社区热度**：970 stars（新项目），Reddit r/LocalLLaMA 有讨论帖，MarkTechPost、i10x.ai 等科技媒体报道，Kimi 官方 X/Twitter 账号正式发布

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-07-30 | #11 | 970 | +216 |
