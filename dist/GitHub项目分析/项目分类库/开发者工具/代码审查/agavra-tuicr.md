# agavra/tuicr

> 带 Vim 键绑定的终端代码审查工具——支持 GitHub/GitLab 真实 PR Review 提交

## 基本信息
- **仓库链接**：https://github.com/agavra/tuicr
- **主语言**：Rust
- **Star**：总计 2,137 | 今日新增 +336
- **首次上榜**：2026-08-01
- **最近上榜**：2026-08-01
- **累计上榜**：1 次

## 知识归类
B-开发者工具 › 代码审查 › 终端审查TUI

## 详细介绍
tuicr（发音 "tweaker"）是一个终端 UI（TUI）代码审查工具，提供 GitHub 风格的连续差异查看器，可以在终端中流畅滚动浏览所有改动文件。核心亮点是完整的 Vim 键绑定模型（j/k 导航、c 评论、y 复制、:submit 提交），支持行级、范围级、文件级和 Review 级四层评论粒度。审查完成后可将评论直接推送为 GitHub 或 GitLab 的真实 PR Review（包括 Approve / Comment / Request changes），也可复制结构化 Markdown 粘贴给 AI 编程助手处理。自动检测 git、jj（Jujutsu）、mercurial 三种版本控制系统。与 hunk、lumen、gh pr review 等同类工具相比，tuicr 是唯一同时支持完整 Vim 模型、GitHub + GitLab 双平台 PR 提交、jj/hg 兼容且单二进制分发的工具。

## 适用领域
习惯终端工作流的开发者、Vim/Neovim 用户、需要人机协作审查 AI 生成代码的开发者、使用 jj 或 mercurial 的团队。

## 背景调研
- **开发团队**：agavra（Almog Gavra），开源仓库，项目官网 tuicr.dev
- **融资/商业化**：MIT 开源，crates.io / Homebrew / mise / Nix 多渠道分发，无商业化模式
- **社区热度**：2.1K stars，172 forks，349 commits；LinkedIn 上有开发者讨论其"human-in-the-loop code review for AI-generated changes"的定位，被 GitCode 等平台镜像收录

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-01 | #8 | 2,137 | +336 |
