# FxEmbed/FxEmbed

> 在链接里加两个字母，X/Bluesky 的视频、多图、投票就能在 Discord 里正常显示——FxTwitter/fixupx 背后的引擎

## 基本信息
- **仓库链接**：https://github.com/FxEmbed/FxEmbed
- **主语言**：TypeScript
- **Star**：总计 5,363 | 今日新增 +182
- **首次上榜**：2026-09-25
- **最近上榜**：2026-09-25
- **累计上榜**：2 次

## 知识归类
C-前端/Web › 社交嵌入服务 › 链接嵌入修复

## 详细介绍
FxEmbed 是 FxTwitter、FixupX、FxBluesky 三个服务的统一代码库，解决 X/Twitter 和 Bluesky 链接在 Discord、Telegram 等平台嵌入体验糟糕的老问题——视频放不出来、多图只显示一张、投票和引用看不见。用法极简：twitter.com 前面加 fx 变成 fxtwitter.com，x.com 变成 fixupx.com，bsky.app 变成 fxbsky.app，嵌入立刻恢复完整功能，还附赠翻译等增强。技术上跑在 Cloudflare Worker 上，按 Host header 路由多个域名，Docker 镜像通过 Wrangler 跑本地 workerd 运行时（用 node:24-bookworm-slim 而非 Alpine，因 workerd 依赖 glibc）；支持完全自托管，可自定义域名、品牌和凭据。作为 2022 年创建的老牌社区项目，FxTwitter 已是 Discord 社区的事实标准小技巧——连 wikiHow 都写了教程，Reddit 的 iOS 快捷指令社区也有专门转换工具。MIT 许可，Crowdin 多语言协作，状态页公开 30 天可用率。

## 适用领域
Discord/Telegram 社区管理员与活跃用户（让分享的推文正常显示）；想自托管嵌入代理、定制品牌的社区运营者；研究 Cloudflare Worker 多域名路由、OG 协议元数据注入的 Web 开发者

## 背景调研
- **开发团队**：FxEmbed 组织维护的社区项目，2022-07 创建，GitHub 上有完整 CI（构建/测试/状态徽章）
- **融资/商业化**：无商业化，MIT 开源，接受 PR；靠 Crowdin 众包翻译文档
- **社区热度**：fxtwitter/fixupx 是 Discord 圈广泛流传的实用技巧，docs.fxembed.com 提供完整文档与 API 参考，状态页 uptime 徽章公开

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-09-25 | #6 | 5,363 | +182 |
