# Homebrew/BrewUI

> Homebrew 官方 macOS 图形界面：不碰终端也能管好软件包

## 基本信息
- **仓库链接**：https://github.com/Homebrew/BrewUI
- **主语言**：Swift
- **Star**：总计 1,316 | 今日新增 +356
- **首次上榜**：2026-09-16
- **最近上榜**：2026-09-16
- **累计上榜**：1 次

## 知识归类
B-开发者工具 › 包管理工具 › Homebrew图形界面

## 详细介绍
Homebrew 官方组织出品的原生 macOS GUI，目标很明确：让不喜欢终端的用户也能安全地发现、安装、更新和管理 brew 包，同时坚持「完全透明」——绝不隐藏 Homebrew 底层在做什么，每个操作都看得见。技术栈是 Swift 6.0（严格并发）+ SwiftUI + Swift Package Manager，要求 macOS Tahoe 26+，数据来自 brew CLI 和 Homebrew JSON API。一个值得学习的工程细节：它始终通过干净的 zsh 环境启动 brew（禁用用户 shell 配置文件），Homebrew 的环境变量统一放在 brew.env 文件里管理，避免用户 shell 别名和自定义 PATH 污染安装过程。安装只需 brew install --cask homebrew-app。

## 适用领域
习惯图形界面的 macOS 用户；给非技术亲友远程维护 Mac 的场景；想要可视化查看包依赖与更新状态的开发者。

## 背景调研
- **开发团队**：Homebrew 官方组织（Maintenance Lead: Mikaela Mayer 等核心团队），brew 官方 cask 名为 homebrew-app
- **融资/商业化**：BSD-2-Clause 开源，Homebrew 项目本身靠 GitHub Sponsors 赞助维持
- **社区热度**：Homebrew 主仓库几十万 star，BrewUI 作为官方 GUI 刚起步即上榜，今日 +356
