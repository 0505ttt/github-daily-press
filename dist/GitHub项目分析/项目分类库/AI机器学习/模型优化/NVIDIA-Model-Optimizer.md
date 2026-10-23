# NVIDIA/Model-Optimizer

> NVIDIA 官方模型压缩工具箱：量化、剪枝、蒸馏、NAS 一条龙，产出可直接上 vLLM/TensorRT 的量化 checkpoint

## 基本信息
- **仓库链接**：https://github.com/NVIDIA/Model-Optimizer
- **主语言**：Python
- **Star**：总计 4,725 | 今日新增 +354
- **首次上榜**：2026-09-25
- **最近上榜**：2026-09-27
- **累计上榜**：3 次

## 知识归类
A-AI/机器学习 › 模型优化 › 量化压缩

## 详细介绍
NVIDIA Model Optimizer（ModelOpt）是一站式模型优化库，把量化、剪枝、神经架构搜索（NAS）、蒸馏、投机解码、稀疏化等 SOTA 压缩技术统一到一套 Python API 里。工作流是「输入 → 优化 → 导出」：接受 Hugging Face/PyTorch/ONNX 模型，自由组合优化技术后导出量化 checkpoint，直接在 TensorRT-LLM、TensorRT、vLLM、SGLang 等推理框架部署，统一导出 API 同时支持 transformers 和 diffusers 模型。它是 NVIDIA NVFP4（Blackwell GPU 的 4bit 浮点格式）生态的核心工具：2026-09-16 刚发布 Qwen3.6-35B-A3B 的端到端 W4A4 NVFP4 + 量化感知蒸馏教程，做到 vLLM 吞吐 1.30 倍、checkpoint 缩小 3.1 倍且精度无损；官方 GLM-5.2-NVFP4（753B MoE → 4bit）也是用它产出。与纯 PTQ 工具的区别：与 Megatron-LM、Megatron-Bridge、HF Accelerate 训练侧深度集成，支持 QAD（量化感知蒸馏）这类需要训练配合的技术，覆盖从压缩到恢复精度的全链路。

## 适用领域
需要把大模型塞进有限显存做推理部署的算法/推理工程师；基于 Blackwell GPU 做 FP4 量化上线的团队；研究模型压缩（剪枝+蒸馏+量化组合拳）的工程师与研究生

## 背景调研
- **开发团队**：NVIDIA 官方维护，文档站 nvidia.github.io/Model-Optimizer，配套 build.nvidia.com 官方 Playbook 教程
- **开源许可**：Apache-2.0，PyPI 包 nvidia-modelopt
- **社区热度**：Nemotron 3 全系（Ultra 550B/Lightning）官方 NVFP4 checkpoint 均由 ModelOpt 产出；Domyn、Bielik.AI 等公司公开用其 Minitron 剪枝+蒸馏压缩自研模型（如 355B→260B、7B 缩 33% 快 50%）

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-09-25 | #5 | 4,071 | +44 |
| 2026-09-27 | #3 | 4,725 | +354 |
