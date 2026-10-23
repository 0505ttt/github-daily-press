# agalwood/Motrix

> 界面清爽的全功能下载管理器——HTTP/BT/磁力链全支持，v2「Turbo」重写进行中

## 基本信息
- **仓库链接**：https://github.com/agalwood/Motrix
- **主语言**：TypeScript
- **Star**：总计 53,635 | 今日新增 +607
- **首次上榜**：2026-08-18
- **最近上榜**：2026-08-19
- **累计上榜**：2 次

## 知识归类
I-系统/底层 › 下载工具 › 跨平台下载管理器

## 详细介绍
Motrix 是老牌开源下载管理器，支持 HTTP、FTP、BitTorrent、磁力链接等主流协议，界面现代清爽、保持简单易用。v2 版本「Motrix Turbo」用 Electron + React + TypeScript 从零重写：下载核心与 UI 彻底分离，浏览器扩展和 CLI 通过自研开放协议 MDXP（基于 JSON-RPC 2.0 的 Motrix Download eXchange Protocol）与主程序通信，插件运行在 QuickJS 沙箱并有细粒度权限 + 应用内插件市场。同一核心支持两种形态：跨平台桌面应用（macOS/Windows/Linux）和 Headless 服务器模式（Node.js 直跑或 Docker，自带 Web UI，面向 NAS 与家庭服务器）。BT 下载支持单文件选择、tracker 列表自动更新与健康检查、UPnP/NAT-PMP 端口映射、SQLite 会话恢复；官方 CLI @motrix/cli 适配日常 shell 与 AI Agent 调用。v2 目前处于 beta（v2.0.0-beta.18），官方提示迁移前务必备份 v1 数据。

## 适用领域
替代 IDM/迅雷的日常下载工具、NAS 用户跑 Headless 模式集中管理下载、需要浏览器扩展一键接管的用户、对插件生态与开放协议感兴趣的开发者。

## 背景调研
- **开发团队**：agalwood（个人开发者），仓库创建于 2018 年 12 月，中文开源社区老牌项目
- **融资/商业化**：无融资，自定义开源协议（NOASSERTION）；v1 曾因作者精力有限长期低维护，v2 重写后恢复活跃
- **社区热度**：53K stars、4.9K forks，小众下载器类目中的星数天花板；中文社区（知乎下载工具盘点、B 站）常客，v2 beta 的 MDXP 开放协议与 QuickJS 插件沙箱设计在 Hacker News 类社区引发新一波关注

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-18 | #11 | 53,025 | +295 |
| 2026-08-19 | #8 | 53,635 | +607 |
