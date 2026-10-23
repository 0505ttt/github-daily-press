# Lakr233/vphone-cli

> 在 Mac 上启动一台虚拟 iPhone：基于 Apple Virtualization.framework 与 PCC 研究 VM 基础设施

## 基本信息
- **仓库链接**：https://github.com/Lakr233/vphone-cli
- **主语言**：Swift
- **Star**：总计 9,634 | 今日新增 +361
- **首次上榜**：2026-09-17
- **最近上榜**：2026-09-17
- **累计上榜**：2 次

## 知识归类
H-移动开发 › iOS虚拟化 › 虚拟iPhone启动器

## 详细介绍
vphone-cli 是一个命令行工具，利用 Apple 的 Virtualization.framework 配合 PCC（Private Cloud Compute）研究虚拟机基础设施，直接在 Apple Silicon Mac 上启动一台运行 iOS 26 的虚拟 iPhone。工作流是：创建空 VM → 下载并合并 iPhone/CloudOS IPSW 固件 → 给引导链打补丁 → 安装 CFW → 首次启动。提供五档固件变体（less/regular/dev/jb/exp），安全绕过程度递增：从只打 4 个补丁、保留全部 iOS 安全缓解的 patchless 版，到 141 个补丁、带完整越狱（Sileo/TrollStore 自动装）加反虚拟机检测的研究版。运行门槛：Apple Silicon + macOS 15+ + Xcode + 放宽 SIP/AMFI 以使用私有 PV=3 entitlement。仓库附 research/ 目录逐组件对比二进制补丁差异，工程文档非常扎实。

## 适用领域
iOS 安全研究与越狱研究（不用真机就能跑可调试的 iOS）；逆向工程师做动态分析；探索 iOS 自动化测试可能性的移动开发者。

## 背景调研
- **开发团队**：Lakr233，知名 macOS/iOS 开发者（活跃开源作者），提供中/英/日/韩四语 README
- **融资/商业化**：MIT 开源，可通过 brew install zqxwce/tap/vphone-cli 安装
- **社区热度**：13.3K star；2026-09-01 Adafruit 博客专题报道《Boot a virtual iPhone on a Mac》；README 明确标注这是 POC（概念验证）性质的研究项目

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-31 | #3 | 9,634 | +361 |
