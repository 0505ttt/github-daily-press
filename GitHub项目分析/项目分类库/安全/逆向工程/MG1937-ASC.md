# MG1937/ASC

> 超快 Android 反编译器前端：352MB APK 全局交叉引用搜索只要 1.79 秒

## 基本信息
- **仓库链接**：https://github.com/MG1937/ASC
- **主语言**：Python
- **Star**：总计 1,140 | 今日新增 +122
- **首次上榜**：2026-09-16
- **最近上榜**：2026-09-16
- **累计上榜**：1 次

## 知识归类
G-安全 › 逆向工程 › Android按需反编译

## 详细介绍
BlackHat Europe Arsenal 议题项目，核心思想是反传统而行：传统反编译器要吃掉数 GB 内存、花几十分钟构建全局索引，而 ASC 直接把编译产物当成只读数据库按需查询——在 Deflate 比特流内部直接探测、构建密集 Huffman 查找表提取元数据，不碰无关数据块；再利用 R8 编译器确定性常量重排与指令去重留下的高密度物理布局，做跨 DEX 闪电搜索；配合 O(1) 指令定位原语实现常数时间方法解析，无需构建重映射表。命中目标后只抽取该类的字节码及其依赖，在内存中动态重建一个最小自洽 DEX 立即反编译。实测 352MB 商业 APK：全局交叉引用 1.79 秒、反编译目标类 177 毫秒、仅占 141MB 内存。pip install droidasc 即可用，提供 getclass/getmanifest/findrefs 三个子命令和 GUI。

## 适用领域
Android 安全研究与大规模 APK 审计；移动逆向工程师快速定位目标类；为 Agent/自动化分析提供毫秒级反编译原语（README 明确定位 Agents/Mobile Researchers）。

## 背景调研
- **开发团队**：MG1937（独立安全研究员），成果入选 BlackHat Europe 2026 Arsenal 议题「Droid ASC: R8 Compiler Optimization as a Decompiler Primitive」
- **融资/商业化**：开源（PyPI 发行为 droidasc），暂无商业化
- **社区热度**：1.1K star 新项目，与同榜的 ghidra 形成「逆向双雄」话题
