# manaflow-ai/cmux

> 基于 Ghostty 的 macOS 原生终端——竖排标签页 + 智能通知，专为并行跑 AI 编程 Agent 打造

## 基本信息
- **仓库链接**：https://github.com/manaflow-ai/cmux
- **主语言**：Swift
- **Star**：总计 27,819 | 今日新增 +96
- **首次上榜**：2026-10-08
- **最近上榜**：2026-10-08
- **累计上榜**：1 次

## 知识归类
B-开发者工具 › 终端工具 › AI编程专用终端

## 详细介绍
cmux 是 manaflow-ai 开源的 macOS 终端，解决一个具体痛点：同时并行跑多个 Claude Code / Codex 会话时，原生通知只有一句"Claude is waiting for your input"毫无上下文，标签一多连标题都读不清。它用 Swift/AppKit 编写（非 Electron），基于 libghostty 做 GPU 加速渲染，直接读取你现有的 ~/.config/ghostty/config 主题字体配置。核心增量是侧边栏竖排标签页（显示 git 分支、关联 PR 状态、工作目录、监听端口、最新通知）和通知系统：解析 OSC 9/99/777 终端序列，Agent 等待输入时对应窗格亮蓝色光环、标签页点亮，Cmd+Shift+U 直接跳到最近未读。与 GUI 编排器（多为 Electron/Tauri）的区别在于：它是"原语而非方案"，只给终端+浏览器+通知+CLI，不锁死你的工作流。

## 适用领域
在 macOS 上并行运行多个 AI 编程 Agent（Claude Code、Codex、OpenCode、Gemini CLI 等）的重度用户；喜欢终端流但需要多会话管理的独立开发者；想用 iPhone 远程接入并接收终端通知的移动办公场景。

## 背景调研
- **开发团队**：manaflow-ai 团队，作者自述因并行跑大量 Claude Code/Codex 会话、嫌 GUI 编排器性能差而自建
- **融资/商业化**：开源免费 + 付费的 cmux Founders Edition（含 iOS beta 早期访问等），iOS 版通过 TestFlight 分发
- **社区热度**：27.8K star；内置浏览器脚本 API 移植自 Vercel 的 agent-browser，支持 Claude Code/Codex/Grok/Pi/Amp 等 15+ Agent 的 resume 集成，在 AI 编程工具圈讨论度高

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-10-08 | #9 | 27,819 | +96 |
