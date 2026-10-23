# microsoft/VibeVoice

> 微软开源的前沿语音 AI——统一的语音合成（TTS）+ 语音识别（ASR）平台

## 基本信息
- **仓库链接**：https://github.com/microsoft/VibeVoice
- **主语言**：Python
- **Star**：总计 51,226 | 今日新增 +332
- **首次上榜**：2026-07-30
- **最近上榜**：2026-07-30
- **累计上榜**：1 次

## 知识归类
A-AI/机器学习 › 语音技术 › 前沿语音AI（TTS+ASR）

## 详细介绍
VibeVoice 是微软开源的前沿语音 AI 项目，集成了语音合成（TTS）和语音识别（ASR）两大核心能力。ASR 模块（VibeVoice-ASR）支持单次处理 60 分钟长音频，生成包含说话人、时间戳、内容的结构化转录，原生支持 50+ 种语言，已集成进 Hugging Face Transformers。TTS 模块支持流式语音合成，提供 Colab 在线体验。最新的 VibeVoice-ASR-BitNet 通过异构量化（I8_S + I2_S）将模型从 4.62GB 压缩到 1.58GB，在 3+ CPU 线程上实现实时推理（RTF < 1），无需 GPU。项目已集成到 Azure AI Foundry Labs，微软背书保证了工程质量。与 Whisper 等纯 ASR 模型相比，VibeVoice 提供了语音输入到输出的完整链路。

## 适用领域
语音交互应用开发者、需要长音频转录的媒体/法务团队、多语言语音识别场景、边缘设备上的语音 AI 部署（通过 BitNet 量化版本）；微软 Azure 生态用户可直接在 Foundry Labs 中体验。

## 背景调研
- **开发团队**：微软（Microsoft）语音 AI 研究团队，核心贡献者包括 YaoyaoChang、pengzhiliang 等（pengzhiliang 为通义千问 Wan2.1 系列核心作者）
- **融资/商业化**：MIT 开源，微软 Azure AI Foundry Labs 提供商业化的在线体验入口
- **社区热度**：51K+ stars，Trendshift 上榜，Hugging Face Collection 活跃，已发布多篇 arXiv 论文（TTS Report、ASR Report）

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-07-30 | #8 | 51,226 | +332 |
