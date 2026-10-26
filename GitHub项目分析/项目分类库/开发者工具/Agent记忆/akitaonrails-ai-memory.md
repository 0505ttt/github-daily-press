# akitaonrails/ai-memory

> 给 AI 编程 Agent 装上长期记忆——Claude Code 干到一半换 Codex 接着干

## 基本信息
- **仓库链接**：https://github.com/akitaonrails/ai-memory
- **主语言**：Rust
- **Star**：总计 13,528 | 本周新增 +3,254
- **首次上榜**：2026-08-18
- **最近上榜**：2026-10-26
- **累计上榜**：7 次

## 知识归类
B-开发者工具 › Agent记忆 › 跨厂商会话延续

## 详细介绍
ai-memory 解决编程 Agent 的「失忆」问题：在 Claude Code 里干到一半的任务，切换到 OpenAI Codex 后不用重新解释架构、失败的尝试和待办问题，直接无缝接续。它通过 MCP 配置 + 生命周期钩子接入各家 Agent CLI，支持 Claude Code、Codex、Cursor、Gemini CLI、OpenCode、Devin CLI 等 10 余种工具，跨厂商共享项目记忆。核心机制是把项目历史整理为可检索的长期记忆（不断合并摘要），并以「workstream」形式支持跨工具会话延续（ai-memory run 命令可透明切换 Agent 而不丢上下文）。Rust 编写，提供 Docker 镜像、macOS ARM/x86 原生二进制、Windows 实验版和 systemd 单元等多种部署形态。与各家官方记忆方案的区别在于「厂商中立」——记忆不绑定任何一家 Agent。

## 适用领域
多 Agent CLI 混用重度用户（Claude Code + Codex + Cursor）、长期维护大型项目需要 Agent 记住历史决策的开发者、团队希望沉淀「AI 可读」的项目知识库。

## 背景调研
- **开发团队**：Fabio Akita（akitaonrails，巴西知名 Ruby/Rails 社区元老、博主与视频博主），个人项目，2026 年 5 月创建
- **融资/商业化**：无融资，MIT 开源；作者博客披露其累计使用编程 Agent 超过 600 小时后打造了 ai-jail、ai-memory、ai-usagebar 等一套个人 AI 工具链
- **社区热度**：2K stars 但今日 +207 冲上榜单第 4，增长动能强；作者两篇博文（2026-05-23 发布、2026-07-20 更新「Switch Agents Without Losing the Session」）在 LinkedIn/Reddit r/LocalLLaMA 引发讨论，Reddit 上也出现了对其持久记忆安全性的讨论（记忆可能被恶意网页注入污染）

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-18 | #4 | 1,993 | +207 |
| 2026-08-19 | #3 | 2,687 | +730 |
| 2026-08-21 | #7 | 3,549 | +335 |
| 2026-09-22 | #4 | 7,622 | +217 |
| 2026-10-18 | #6 | 9,937 | +178 |
| 2026-10-20 | #3 | 11,605 | +666 |
| 2026-10-26 | W#9 | 13,528 | +3,254 |
