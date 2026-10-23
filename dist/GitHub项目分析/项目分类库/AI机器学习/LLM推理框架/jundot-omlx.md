# jundot/omlx

> Mac 菜单栏里的 LLM 推理服务器——Apple Silicon 专属，KV 缓存热内存+冷 SSD 分层

## 基本信息
- **仓库链接**：https://github.com/jundot/omlx
- **主语言**：Python
- **Star**：总计 19,809 | 今日新增 +467
- **首次上榜**：2026-08-18
- **最近上榜**：2026-08-20
- **累计上榜**：3 次

## 知识归类
A-AI/机器学习 › LLM推理框架 › AppleSilicon本地推理

## 详细介绍
oMLX 是专为 Apple Silicon 打造的 LLM 推理服务器，基于 Apple 官方 MLX 框架，从 macOS 菜单栏直接启停和监控，下载 DMG 拖进应用程序即用。核心创新是分层 KV 缓存：将 KV cache 持久化到「热内存层 + 冷 SSD 层」，即使对话中途切换上下文，历史上下文仍保持缓存并可跨请求复用，让本地 LLM 在 Claude Code 等编程 Agent 下真正可用（这正是作者造它的动机）。支持连续批处理、块级前缀共享与写时复制缓存，对外提供 OpenAI 兼容接口；可选装 GLM-5.2 / MiniMax M3 原生自定义内核——官方实测 M3 Ultra 上 GLM-5.2 融合 DSA prefill 提速约 30 倍（845 vs 29 tok/s）。需要 macOS 15+ 与 M1 及以上芯片，支持 MCP 可选安装。

## 适用领域
Mac 用户本地跑 LLM 服务编程 Agent（Claude Code/Codex 接本地模型）、内存有限但 SSD 富余的 Apple Silicon 设备、追求「菜单栏一点就跑」低门槛本地推理的用户。

## 背景调研
- **开发团队**：jundot（个人开发者，联系方式 junkim.dot@gmail.com，官网 omlx.ai），2026 年 2 月创建
- **融资/商业化**：无融资，Apache-2.0 开源；README 显示 Kimi（Moonshot）等赞助位
- **社区热度**：18.9K stars、1.6K forks；被 Apple MLX 官方仓库 Discussions 收录推荐（mlx-explore/mlx#3203），Reddit r/LocalLLaMA 与 lobste.rs 均有讨论帖，Medium 出现架构分析长文（连续批处理/块级前缀共享/COW 缓存）

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-18 | #8 | 18,964 | +96 |
| 2026-08-19 | #10 | 19,376 | +366 |
| 2026-08-20 | #8 | 19,809 | +467 |
