"""引用错配、编造精确数字与入口链接的回归。"""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from gh_daily import sources
from gh_daily.build import build_site
from gh_daily.privacy import PATTERNS
from gh_daily.citations import check_text, check_workspace, require_article_url, validate_claim


class CitationTests(unittest.TestCase):
    def test_public_risk_report_slug_is_not_a_secret_but_real_prefixes_are(self):
        pattern = PATTERNS["疑似访问凭据"]
        self.assertIsNone(pattern.search("https://metr.org/blog/2026-10-20-misalignment-risk-report-august-2026-review/"))
        for prefix in ("sk-", "ghp_", "github_pat_"):
            for wrapper in ("Bearer {}", "https://example.org/?key={}", '"api_key": "{}"'):
                self.assertIsNotNone(pattern.search(wrapper.format(prefix + "x" * 30)))

    def test_homepage_feed_and_listing_cannot_support_a_claim(self):
        for url in ("https://www.wsj.com/", "https://www.theinformation.com?x=1",
                    "https://techcrunch.com/feed/", "https://openai.com/news/rss.xml",
                    "https://metr.org/", "https://example.org/category/ai", "https://example.org/search?q=ai"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                require_article_url(url)
        require_article_url("https://www.wsj.com/tech/ai/anthropic-revenue-growth-ipo-accaf0f1")
        require_article_url("https://github.com/owner/repository")

    def test_evidence_must_be_a_real_continuous_passage(self):
        source = {"url": "https://example.org/news/prices", "text": "OpenAI API pricing is unchanged. A separate story discusses agents."}
        item = {"title": "OpenAI 定价说明", "summary": "API 定价保持不变。", "evidence": ["OpenAI API pricing is unchanged."]}
        validate_claim(item, source)
        for quotes in ([], ["Invented evidence that was never published."], ["OpenAI API agents"]):
            with self.subTest(quotes=quotes), self.assertRaises(ValueError):
                validate_claim({**item, "evidence": quotes}, source)

    def test_unrelated_foundation_story_and_unsupported_numbers_are_rejected(self):
        source = {"url": "https://example.org/news/prices", "text": "OpenAI API pricing fell by 60% in one region."}
        evidence = [source["text"]]
        for title, summary in (("OpenAI 捐赠 Agentic AI Foundation", "基金会接受捐赠。"),
                               ("OpenAI 降价 80%", "API 降价。"),
                               ("GPT-5.3-Codex 发布", "OpenAI 发布模型。")):
            with self.subTest(title=title), self.assertRaises(ValueError):
                validate_claim({"title": title, "summary": summary, "evidence": evidence}, source)

    def test_manual_markdown_and_fusion_links_are_checked(self):
        self.assertTrue(check_text('- **财务报道** — 详情。[来源](https://www.wsj.com/)'))
        self.assertTrue(check_text('- **漏引来源** — 没有原文。'))
        self.assertTrue(check_text('<section class="ai-band"><ul><li><a href="https://techcrunch.com/feed/">来源</a></li></ul></section>', html=True))
        self.assertTrue(check_text('<section class="ai-band"><ul><li>没有来源的新闻</li></ul></section>', html=True))
        self.assertFalse(check_text('[导航](https://example.org/)\n- **公告** — 详情。[来源](https://example.org/news/item)'))

    def test_policy_does_not_rewrite_or_block_older_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "AI前沿资讯/日报"
            folder.mkdir(parents=True)
            (folder / "2026-10-25-AI日报.md").write_text('- **旧报** — 详情。[来源](https://www.wsj.com/)', encoding="utf-8")
            self.assertEqual(check_workspace(root), [])
            (folder / "2026-10-26-AI日报.md").write_text('- **新报** — 详情。[来源](https://www.wsj.com/)', encoding="utf-8")
            self.assertEqual(len(check_workspace(root)), 1)

    def test_feed_date_cannot_disguise_an_old_article_or_missing_body(self):
        feed = '<rss><channel><item><title>新公告</title><link>https://example.org/news/item</link><pubDate>2026-10-26T01:00:00Z</pubDate></item></channel></rss>'
        bodies = ('<meta property="article:published_time" content="2026-02-05T00:00:00Z"><main><h1>旧模型</h1><p>这是旧模型的发布原文内容。</p></main>',
                  '<h1>订阅查看</h1>',
                  '<main><h1>无日期文章</h1><p>这是没有可验证日期的原文内容。</p></main>')
        for body in bodies:
            def fetch(url, **_):
                if url.endswith("/feed"):
                    return feed
                if "bing.com" in url:
                    return '<rss><channel></channel></rss>'
                return body
            with self.subTest(body=body), patch.object(sources, "AI_SOURCES", (("来源", "https://example.org/feed", "feed"),)), patch.object(sources, "fetch", side_effect=fetch):
                result = sources.collect_ai(now=datetime(2026, 10, 26, 2, tzinfo=timezone.utc))
            self.assertEqual(result["articles"], [])

    def test_recommendation_date_does_not_date_the_article(self):
        body = '<main><h1>旧文章</h1><p>正文没有已知发布日期。</p><aside><time datetime="2026-10-26T08:00:00+08:00"></time></aside></main>'
        with patch.object(sources, "fetch", return_value=body), self.assertRaises(sources.SourceError):
            sources.verify_article({"url": "https://example.org/news/item"}, deadline=float("inf"))

    def test_feed_summary_is_replaced_with_opened_article_text(self):
        body = '<meta property="article:published_time" content="2026-10-26T01:00:00Z"><main><h1>实际公告</h1><p>实际正文没有任何价格数字。</p><aside>降价 80%</aside></main>'
        with patch.object(sources, "fetch", return_value=body):
            result = sources.verify_article({"url": "https://example.org/news/item", "text": "错误 RSS 摘要：降价 80%"}, deadline=float("inf"))
        self.assertIn("实际正文", result["text"])
        self.assertNotIn("80%", result["text"])

    def test_duplicate_failed_article_is_not_retried_by_other_sources(self):
        feed = '<rss><channel><item><title>公告</title><link>https://example.org/news/item</link><pubDate>2026-10-26T01:00:00Z</pubDate></item></channel></rss>'
        def fetch(url, **_):
            if url.endswith("/feed"):
                return feed
            raise sources.SourceError("原文访问失败")
        with patch.object(sources, "AI_SOURCES", (("来源一", "https://example.org/feed", "feed"), ("来源二", "https://other.org/feed", "feed"))), patch.object(sources, "fetch", side_effect=fetch) as request:
            result = sources.collect_ai(now=datetime(2026, 10, 26, 2, tzinfo=timezone.utc))
        self.assertEqual(result["articles"], [])
        self.assertEqual(sum(call.args[0] == "https://example.org/news/item" for call in request.call_args_list), 1)

    def test_repository_identity_is_in_api_evidence(self):
        import json
        payload = {"items": [{"full_name": "sample/project", "html_url": "https://github.com/sample/project", "created_at": "2026-10-26T01:00:00Z", "description": "A useful API tool", "stargazers_count": 2}]}
        with patch.object(sources, "AI_SOURCES", (("GitHub", "https://api.github.com/search/repositories", "github"),)), patch.object(sources, "fetch", return_value=json.dumps(payload)):
            result = sources.collect_ai(now=datetime(2026, 10, 26, 2, tzinfo=timezone.utc))
        source = result["articles"][0]
        validate_claim({"title": "sample/project", "summary": "API 工具", "evidence": [source["text"]]}, source)

    def test_build_rejects_bad_reference_before_replacing_existing_site(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "AI前沿资讯/日报"
            folder.mkdir(parents=True)
            (folder / "2026-10-26-AI日报.md").write_text('- **新闻** — 详情。[来源](https://www.wsj.com/)', encoding="utf-8")
            (root / "dist").mkdir()
            (root / "dist/index.html").write_text("上一版页面", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "引用检查未通过"):
                build_site(root)
            self.assertEqual((root / "dist/index.html").read_text(encoding="utf-8"), "上一版页面")


if __name__ == "__main__":
    unittest.main()
