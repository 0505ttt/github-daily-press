# trycua/cua

> 给 AI Agent 一台能用的电脑——开源的 Computer-Use 2.0 全栈基础设施

## 基本信息
- **仓库链接**：https://github.com/trycua/cua
- **主语言**：Rust
- **Star**：总计 28,713 | 今日新增 +229
- **首次上榜**：2026-10-08
- **最近上榜**：2026-10-08
- **累计上榜**：4 次

## 知识归类
A-AI/机器学习 › Computer-Use › 桌面自动化基础设施

## 详细介绍
cua（读 "koo-ah"）是 Computer-Use Agent 的开源全栈基础设施，一个仓库装下四大件：Cua Spaces（给 Agent 分配完整桌面的应用，macOS VM 在本机构建、Linux/Omarchy 镜像、可跑在自己 Mac 或自己云账号上）、Cua Driver（macOS/Windows/Linux 三平台的桌面自动化驱动）、Lume（基于 Apple Virtualization.Framework 的本地 VM 管理）、CUA-S1（专注表单等快速有界决策的小型 System 1 模型）外加 Cua Bench（评测与训练数据生成，可导出轨迹做 RL）。其 "Computer-Use 2.0" 理念是让 Agent 在同一个任务里于代码、API、图形界面之间自由切换。SDK 覆盖 Python/TypeScript/Swift/Kotlin，沙箱内不需要装 Agent——就绪探测靠运行时和端口探针，带 cua-spacesd 守护进程的镜像额外提供进程/文件/截图/低延迟音视频流。与同类（纯浏览器自动化）的区别是跨操作系统、覆盖整个桌面而非仅网页。

## 适用领域
构建桌面自动化 Agent 的 AI 工程师；需要在隔离 VM 里安全跑 Claude Code/Codex 等编程 Agent 并行任务的团队；做 Computer-Use 模型训练、评测和数据采集的研究者；想在 Mac 上本地管理 macOS/Linux 虚拟机的开发者。

## 背景调研
- **开发团队**：Cua 团队（trycua），YC X25 批次公司，创始人长期在 X 上连载 "The Story of Computer-Use"
- **融资/商业化**：YC 孵化，开源核心 + Cua Spaces 云服务商业化（支持接入自己的 AWS/GCP/Modal 账号）
- **社区热度**：28.7K star；曾在 ClawCon 演示 CuaBot 多人计算机使用（Agent 和人各有独立光标/键盘焦点），被 OpenClaw 社区和 HN 广泛讨论

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-09-20 | #2 | 24,285 | +383 |
| 2026-09-21 | #4 | 25,176 | +1,018 |
| 2026-09-22 | #2 | 25,653 | +609 |
| 2026-10-08 | #10 | 28,713 | +229 |
