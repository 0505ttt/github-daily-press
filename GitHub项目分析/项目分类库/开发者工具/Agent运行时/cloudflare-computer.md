# cloudflare/computer

> 给 AI Agent 一台虚拟"计算机"——运行在 Cloudflare Durable Object 里的可执行虚拟文件系统

## 基本信息
- **仓库链接**：https://github.com/cloudflare/computer
- **主语言**：TypeScript
- **Star**：总计 4,729 | 今日新增 +2,690
- **首次上榜**：2026-08-06
- **最近上榜**：2026-08-07
- **累计上榜**：2 次

## 知识归类
B-开发者工具 › Agent运行时 › 虚拟计算机

## 详细介绍
Cloudflare 出品的 Computer 是一个驻留在 Durable Object 内的虚拟文件系统，状态以 SQLite 为权威来源，并通过 `workspace.runtime` 暴露一个可插拔的执行入口。目前提供三种后端：Container（把 SQLite 状态投影进沙箱容器做真实 FUSE 挂载，完整 Linux 用户态）、Isolate shell（在 Dynamic Worker 中运行 just-bash）、Isolate JavaScript（在全新 Dynamic Worker 中执行 ECMAScript 模块）。核心卖点是让 AI Agent 拥有一块持久、可写、可执行代码的"工作目录"——Agent 能读写文件、跑命令、调 pandoc 生成 PDF，全部在 Cloudflare 边缘完成。区别于传统 E2B/沙箱方案，它把状态权威地收在 Durable Object 里，天然带强一致性。当前为 PREVIEW 预览阶段，API 不稳定，尚不适合生产。

## 适用领域
AI Agent 基础设施开发者、需要在云上给 Agent 提供持久工作空间的团队、Cloudflare Workers 生态用户、研究 Agent 代码执行与文件持久化的开发者。

## 背景调研
- **开发团队**：Cloudflare 官方团队（@aron-cf、@ndisidore、@ghostwriternr 等），属于 Cloudflare 边缘计算与 AI 基础设施方向的前沿实验
- **融资/商业化**：Apache 2.0 开源，依托 Cloudflare Workers 平台商业化，仓库明确标注 PREVIEW ONLY，当前不接受 unsolicited PR
- **社区热度**：上线即空降 Trending，两天内冲到 4.7K stars，今日 +2,690 为榜单第二高增量，被视作 Cloudflare 在 Agent 基础设施赛道对 E2B、Modal Sandbox 等的正面回应

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-06 | #1 | 2,742 | +796 |
| 2026-08-07 | #3 | 4,729 | +2,690 |
