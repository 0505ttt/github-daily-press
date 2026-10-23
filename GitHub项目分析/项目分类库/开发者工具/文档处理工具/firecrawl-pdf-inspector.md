# firecrawl/pdf-inspector

> 极速 PDF 解析库——本地 200ms 内智能分类并提取文本转 Markdown，无需 OCR

## 基本信息
- **仓库链接**：https://github.com/firecrawl/pdf-inspector
- **主语言**：Rust
- **Star**：总计 17,881 | 今日新增 +545
- **首次上榜**：2026-08-06
- **最近上榜**：2026-09-02
- **累计上榜**：3 次

## 知识归类
B-开发者工具 › 文档处理工具 › PDF解析

## 详细介绍
Firecrawl 团队用 Rust 打造的 PDF 检查/分类/文本提取库，专为"约 54% 的文本型 PDF 根本不需要 OCR"这一洞察而设计。它能用 10-50ms 采样判断 PDF 是文本型、扫描型、图像型还是混合型，并给出逐页 OCR 路由建议和置信度；对文本型 PDF 做带位置感知的提取，自动识别多栏排版、表格、标题层级（按字号比例）、列表、代码块，输出干净 Markdown。在 opendataloader-bench（200 篇 PDF）基准上，pdf-inspector 以 0.875 总分、0.470s 总耗时全面领先 pymupdf4llm、markitdown 等。提供 Python、Node.js、浏览器 WebAssembly 三套绑定，纯 Rust 无 ML 模型无外部服务。

## 适用领域
RAG/文档智能流水线开发者、需要大批量低成本解析 PDF 的团队、爬虫与数据抽取工程师、在浏览器端本地解析 PDF 的前端应用。

## 背景调研
- **开发团队**：Firecrawl（firecrawl.dev），知名 AI 网页抓取/转换服务公司，曾获 YC 等投资，pdf-inspector 是其文档处理产品线的基础组件
- **融资/商业化**：MIT 开源，Crates.io / npm / PyPI 三端发布，服务 Firecrawl 的商业 SaaS 产品
- **社区热度**：12.4K+ stars，今日 +1,194 为榜单最高增量，在文档解析赛道是 markitdown、unstructured 等的有力竞争者

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|---------|----------|---------|
| 2026-08-06 | #9 | 11,360 | +1,583 |
| 2026-08-07 | #13 | 12,360 | +1,194 |
| 2026-09-02 | #7 | 17,881 | +545 |
