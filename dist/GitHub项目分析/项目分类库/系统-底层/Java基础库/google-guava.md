# google/guava

> Google 官方 Java 核心库——集合、并发、缓存的瑞士军刀

## 基本信息
- **仓库链接**：https://github.com/google/guava
- **主语言**：Java
- **Star**：总计 51,617 | 今日新增 +35
- **首次上榜**：2026-08-07
- **最近上榜**：2026-08-07
- **累计上榜**：1 次

## 知识归类
I-系统/底层 › Java基础库 › Google核心库

## 详细介绍
Guava 是 Google 内部广泛使用的 Java 核心库集合，包含新集合类型（Multimap、Multiset、BiMap）、不可变集合、图库（Graph），以及并发（ListenableFuture、RateLimiter）、I/O、缓存（Cache/LoadingCache）、哈希、原语、字符串处理等工具。提供 JRE 和 Android 两种构建版本，JRE 版要求 JDK 1.8+，Android 版兼容移动端。几乎所有 Google 内部的 Java 项目都在使用它，也是 Java 生态中 star 数最高的基础设施库之一。当前稳定版本 33.6.0，通过 Maven/Gradle 一行依赖引入。

## 适用领域
所有 Java/JVM 开发者；Android 应用开发者；需要高质量集合工具、并发原语、缓存方案的后端团队；追求代码简洁和健壮性的 Java 工程师。场景：替代手写的通用工具类、统一团队编码标准、减少对 Apache Commons 等多库的依赖。

## 背景调研
- **开发团队**：Google Java Core Libraries 团队（cpovirk、cgdecker、kluever、lowasser 等），Google 官方维护
- **融资/商业化**：Apache 2.0 开源，Google 官方项目，无独立商业化
- **社区热度**：51.6K stars，11.2K forks，7,457 commits，是 Java 生态的"事实标准"库，被几乎所有 Java 项目间接或直接依赖，文档和 Wiki 极其完善
