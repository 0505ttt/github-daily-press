# agent-substrate/substrate

> Google 出品的 Agent 执行底座：一台机器上「塞」下百万级沙箱，闲置即休眠

## 基本信息
- **仓库链接**：https://github.com/agent-substrate/substrate
- **主语言**：Go
- **Star**：总计 3,460 | 今日新增 +560
- **首次上榜**：2026-09-23
- **最近上榜**：2026-09-24
- **累计上榜**：3 次

## 知识归类
E-基础设施/DevOps › Agent基础设施 › 沙箱运行时

## 详细介绍
安全默认的 Agent 执行运行时，目标是以比标准容器高 10 倍的密度运行数百万沙箱：利用「Agent 大部分时间在闲着」的特性，把大量 actor（智能体实例）复用到少量常驻 worker 上，实测 8 个物理 Pod 承载约 250 个有状态 actor，超卖 30 倍以上。核心指标：suspend/resume 恢复操作低于 500ms、每秒超 500 次挂起/唤醒，唤醒时 RAM 与文件系统状态通过全量快照完整保留。基于 Kubernetes 做 Pod 级供给，内核层用 gVisor/microVM 做零信任隔离，框架无关——ADK、LangChain、Claude Code、MCP Server 都能跑。与 Firecracker 类方案的差异点在「为 Agent 而生」：不是 SDK，是规模化运行 Agent 的系统层。

## 适用领域
平台工程师与 Agent 基础设施团队：大规模托管编码/自主智能体时的沙箱调度层；云厂商与私有化部署场景降本（闲置即冻结）；K8s 运维背景想切入 AI Infra 的工程师

## 背景调研
- **开发团队**：agent-substrate 组织（Google 背景工程师发起，README 注明「非 Google 官方支持产品」）
- **生态位**：Google Cloud 博客同期官宣的 Agent Executor（google/ax）即构建于其上；CNCF 沙箱项目 kagent 已宣布采用
- **社区热度**：每周四 PST 10:00-11:00 社区例会（有录像存档），CNCF Slack 设 #substrate-users / #substrate-dev 频道
- **项目状态**：早期开发阶段，API 不保证向后兼容，官方明确「未准备好生产使用」

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-21 | #9 | 1,366 | +66 |
| 2026-09-23 | #2 | 3,197 | +245 |
| 2026-09-24 | #8 | 3,460 | +560 |
