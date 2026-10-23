# esengine/DeepSeek-Reasonix

> DeepSeek 原生的终端 AI 编码 Agent——围绕 prefix-cache 稳定性工程化设计

## 基本信息
- **仓库链接**：https://github.com/esengine/DeepSeek-Reasonix
- **主语言**：Go（新版 main-v2 分支）/ TypeScript（旧版维护模式）
- **Star**：总计 32,339 | 今日新增 +894
- **首次上榜**：2026-08-06
- **最近上榜**：2026-08-07
- **累计上榜**：2 次

## 知识归类
B-开发者工具 › AI编程工具 › 终端编码Agent

## 详细介绍
Reasonix 是专为 DeepSeek 模型打造的终端编码 Agent（已从 TypeScript 重写为 Go，新版本在 main-v2 分支）。它的核心差异化在于"缓存稳定性不是开关，而是整个循环设计的不变量"——把每一层都调校到 DeepSeek 字节稳定的 prefix-cache 机制上。真实案例：单日 4.35 亿输入 Token，缓存命中 99.82%，花费约 12 美元，而无缓存同等负载需约 61 美元。支持 SEARCH/REPLACE 编辑模式（落地前不碰磁盘）、跨平台（macOS/Linux/Windows），通过 npm 全局安装或 npx 一次性运行。oosmetrics 评为 Agent/LLM/CLI 三个榜单的速度前列。

## 适用领域
使用 DeepSeek 模型做 AI 编码的开发者、追求长会话低成本高缓存命中的重度 Agent 用户、终端原生工作流的工程师。

## 背景调研
- **开发团队**：esengine 团队，中英日三语社区运营，有 Discord 社区，AtomGit 镜像分发
- **融资/商业化**：开源（npm 包 reasonix / dsnix），DeepSeek API 深度绑定，主打"DeepSeek-native"差异化定位
- **社区热度**：32.3K+ stars，在 DeepSeek 生态的编码 Agent 赛道是头部项目，oosmetrics 速度榜 Agent/LLM/CLI 三榜前列

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-06 | #5 | 31,544 | +747 |
| 2026-08-07 | #11 | 32,339 | +894 |
