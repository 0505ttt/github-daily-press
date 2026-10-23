# Lightricks/LTX-2

> 首个 DiT 架构音视频一体生成模型——同步音频+视频，生产级输出，开放权重

## 基本信息
- **仓库链接**：https://github.com/Lightricks/LTX-2
- **主语言**：Python
- **Star**：总计 8,896 | 今日新增 +201
- **首次上榜**：2026-08-14
- **最近上榜**：2026-08-14
- **累计上榜**：1 次

## 知识归类
A-AI/机器学习 › 视频生成 › 音视频一体模型

## 详细介绍
LTX-2 是 Lightricks 推出的首个基于 DiT（Diffusion Transformer）架构的音视频基础模型，在一个模型中集成了现代视频生成的所有核心能力：同步音频和视频生成、高保真输出、多种性能模式、生产级质量、API 访问和开放权重。核心模型 LTX-2.5 为 22B 参数 Transformer，搭配 Gemma 4 12B 文本编码器、独立的视频 VAE 和音频 VAE。提供丰富的 Pipeline 选项：DistilledPipeline（最快推理，8 步生成）、DFRPipeline（细节保真渲染，含空间和时间上采样）、TI2VidTwoStagesPipeline（生产级文/图生视频）、ICLoraPipeline（视频到视频变换）、A2VidPipeline（音频驱动视频生成）、KeyframeInterpolationPipeline（关键帧插值）等。支持 LoRA 微调训练，论文已发布（arXiv:2601.03233）。

## 适用领域
视频内容创作者、AI 视频生成研究者、需要生产级音视频生成的创意团队、VFX/后期制作工程师、对 DiT 架构视频模型感兴趣的开发者。

## 背景调研
- **开发团队**：Lightricks（位于以色列耶路撒冷），知名移动创意应用公司（Facetune、Videoleap 母公司），核心贡献者包括 michaellightricks、AlexeyKravtsov1987 等，官网 ltx.io
- **融资/商业化**：自定义协议（权重开放但有使用条款），提供 LTX Console 在线 Playground；Lightricks 本身是上市公司
- **社区热度**：8.9K stars、1.4K forks，项目创建于 2026 年 1 月；有 Discord 社区和 arXiv 论文支撑，HuggingFace 开放模型下载
