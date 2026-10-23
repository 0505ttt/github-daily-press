# github/gh-stack

> GitHub 官方堆叠式 PR（Stacked PRs）管理工具——把大改动拆成可审查的小 PR 链

## 基本信息
- **仓库链接**：https://github.com/github/gh-stack
- **主语言**：Go
- **Star**：总计 798 | 今日新增 +90
- **首次上榜**：2026-08-02
- **最近上榜**：2026-08-02
- **累计上榜**：1 次

## 知识归类
B-开发者工具 › 代码协作 › Stacked PR

## 详细介绍
GitHub 官方新推出的 gh CLI 扩展，用于管理 Stacked PRs（堆叠式 Pull Request）。堆叠 PR 是一种把大型改动拆成一串小而可审查的 PR 链的实践——每个分支构建在前一个之上，reviewer 每次只看一层的 diff。gh stack 自动化了创建分支、级联 rebase、设置正确的 PR base、层间导航等繁琐操作，还内置了 git rerere 自动记录冲突解决方案。虽然目前还在私有预览阶段（需加入 waitlist），但已被社区高度关注。还提供 AI Agent 集成技能（gh skill install）。

## 适用领域
大型工程团队、追求细粒度 Code Review 的开源项目维护者、有 Stacked PR 习惯的高级开发者。场景：拆分巨型 feature、级联管理多层依赖改动、提升 PR 审查质量。

## 背景调研
- **开发团队**：GitHub 官方团队，仓库 ID 1151630728，2026 年新建项目
- **融资/商业化**：MIT 开源，Stacked PRs 功能目前处于 private preview，需在 gh.io/stacksbeta 加入 waitlist
- **社区热度**：798 stars，36 forks，虽然 star 数不多但增长率高，是 GitHub 官方近期主推的协作工具

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-02 | #7 | 798 | +90 |
