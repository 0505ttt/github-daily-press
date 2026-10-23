# MakazhanAlpamys/Soup

> 一条 YAML 微调大模型——层流式训练让 8B 模型在 4GB 笔记本 GPU 上跑通

## 基本信息
- **仓库链接**：https://github.com/MakazhanAlpamys/Soup
- **主语言**：Python
- **Star**：总计 1,988 | 今日新增 +456
- **首次上榜**：2026-08-16
- **最近上榜**：2026-08-17
- **累计上榜**：2 次

## 知识归类
A-AI/机器学习 › 模型训练 › 本地微调工具

## 详细介绍
Soup 是一个把 LLM 微调简化到「一个 YAML + 一条命令」的开源 CLI：`pip install "soup-cli[train]"`，`soup init --template chat` 生成配置，`soup train` 开跑。其招牌能力是 Layer Streaming（层流式训练）——把冻结的基座模型挡在 VRAM 之外，逐个 decoder 层喂给 GPU，从而在 4GB 的 RTX 3050 笔记本上微调 Llama-3.1-8B（NF4 量化 + LoRA，实测 119.6 tok/s、峰值显存 3.32GB，且与常驻训练逐位一致，H100 上独立复现）。工具还内建自动批量大小、GPU 检测、量化选择，以及一套 `soup ship` 发布门禁（含 ben­ign-prompt 过度拒答检测和 --noise-floor 噪声地板显著性判定），覆盖「训练→评估→发布」闭环。与 unsloth 定位相近，但 Soup 更强调极简配置和消费级硬件可用性，并有 Zenodo DOI 论文支撑。

## 适用领域
只有游戏本/入门显卡的学生和独立开发者、不想配 SSH 和集群的中小团队（本地 QLoRA 微调）、需要快速验证微调收益的应用团队、关注显存优化技术（层流式加载）的研究者。

## 背景调研
- **开发团队**：MakazhanAlpamys（个人开发者），配官网 trysoup.dev、Discord 社区和 YouTube 频道，商业规划为 Soup Zero 本地 AI 工作台
- **融资/商业化**：Apache-2.0 开源协议，CLI 免费；Layer Streaming 的测量数据发布于 Zenodo（DOI: 10.5281/zenodo.21771064），有 Product Hunt 发布记录
- **社区热度**：1.6K stars、261 forks，仓库创建于 2026 年 2 月；近期通过 Product Hunt 和 X 传播冲上 Trending，提供免费 Colab T4 复现笔记本

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-16 | #7 | 1,625 | +303 |
| 2026-08-17 | #7 | 1,988 | +456 |
