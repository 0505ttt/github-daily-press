# superdesigndev/treg

> 「工具界的 OpenRouter」：一个 token 调 3000+ API，按次计费从一美分起

## 基本信息
- **仓库链接**：https://github.com/superdesigndev/treg
- **主语言**：Python
- **Star**：总计 2,431 | 今日新增 +230
- **首次上榜**：2026-09-23
- **最近上榜**：2026-09-23
- **累计上榜**：1 次

## 知识归类
A-AI/机器学习 › Agent基础设施 › 工具调用市场

## 详细介绍
treg 自述为「OpenRouter，但面向 Agent 工具而非模型」：一个 base URL + 一个 token，即可调用 60+ 供应商的 3000+ API 端点——SEO 与外链、社媒与趋势、企业/人脉信息 enrichment、广告、抓取、图像视频生成——按次计费低至一美分，无需逐家注册。核心设计是「按任务找工具而非按厂商」：treg catalog search "find a work email" 直接按用途检索。凭据阶梯设计很讲究：团队自持 key 的调用永不计量；无 key 时走 treg 的 key 按余额计费；代理层「只转发、不建模」上游请求，凭据服务端注入，调用方永远摸不到密钥。余额耗尽返回结构化 HTTP 402（含余额/预估费用/充值链接），Agent 无需解析自然语言即可自行处理。

## 适用领域
Agent 开发者免去逐家申请 API 的账号管理负担；营销/增长团队按需调用 SEO、社媒、enrichment 数据；小团队用「自己的 key 优先」策略零成本共享内部工具给全组的 Agent

## 背景调研
- **开发团队**：Superdesign 团队（superdesign.dev），托管版 live 在 treg.to（部署于 Render），支持自托管
- **商业模式**：按次计费（低至 1 美分）+ 团队预付余额；新团队一次性赠 $1.00；自家 key 调用永不计量
- **社区热度**：Discord 社区运营；已上架 Claude Connectors Directory、MiniMax 插件市场

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-09-23 | #7 | 2,431 | +230 |
