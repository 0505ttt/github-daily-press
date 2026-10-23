# deepseek-ai/DeepGEMM

> DeepSeek 出品的高性能 GPU 张量核 kernel 库——FP8/FP4/BF16 GEMM 与融合 MoE 一站搞定

## 基本信息
- **仓库链接**：https://github.com/deepseek-ai/DeepGEMM
- **主语言**：CUDA
- **Star**：总计 8,674 | 今日新增 +363
- **首次上榜**：2026-10-06
- **最近上榜**：2026-10-07
- **累计上榜**：2 次

## 知识归类
A-AI/机器学习 › LLM推理优化 › GPU kernel库

## 详细介绍
DeepGEMM 是 DeepSeek 官方开源的统一高性能张量核 kernel 库，把现代大模型推理的关键计算原语——FP8/FP4/BF16 GEMM、带通信重叠的融合 MoE（Mega MoE）、闪电索引器的 MQA 打分、HyperConnection 等——收进一份简洁的 CUDA 代码库。所有 kernel 通过 DeepJIT 在运行时编译，安装时无需 CUDA 编译，部署体验干净利落。设计上借鉴 CUTLASS/CuTe 的概念但避免重度依赖其模板体系，核心 kernel 数量被刻意控制得很少，官方定位之一就是"学习 NVIDIA GPU kernel 优化的干净教材"；尽管轻量，性能在多种矩阵形状下持平甚至超过专家调优的库（H800 上曾跑到 1550 TFLOPS）。2026年9月新增 Ascend 版本（DeepGEMM-Ascend）与局部性域优化。要求 SM90/SM100 架构 GPU（如 H100/H800/B200）+ CUDA 12.9+。

## 适用领域
LLM 推理引擎开发者、GPU kernel 工程师；自部署 DeepSeek 系模型的团队；学习 CUDA/张量核优化的研究生与工程师。

## 背景调研
- **开发团队**：DeepSeek（深度求索）官方
- **融资/商业化**：MIT 开源，服务于 DeepSeek 开源模型生态
- **社区热度**：8.6K star；DeepSeek V3/R1 系列推理栈的核心组件之一，社区视为学 FP8 GEMM 优化的标杆教材

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-10-06 | #9 | 8,596 | +363 |
| 2026-10-07 | #9 | 8,674 | +363 |
