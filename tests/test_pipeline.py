"""采编回归：全部网络与模型都替换为固定证据，不产生收费调用。"""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from gh_daily import pipeline, reports, sources


def snapshot(period="daily", total=1200):
    return {"period": period, "source": f"https://github.com/trending?since={period}", "fetched_at": "2026-06-01T00:30:00+00:00",
            "projects": [{"repo": "sample/project", "url": "https://github.com/sample/project", "rank": 1, "description": "A tool for public data", "readme": "Process public data", "total": total, "growth": 900, "lang": "Python", "category": "B-开发者工具", "usage": "暂未获取"}]}


def ai_collection():
    return {"fetched_at": "2026-06-01T00:30:00+00:00", "window_hours": 48,
            "sources": [{"source": "OpenAI", "status": "success", "count": 1}],
            "articles": [{"id": "S1", "title": "公开公告", "source": "OpenAI", "url": "https://openai.com/news/example", "published_at": "2026-05-31T12:00:00+00:00", "text": "公开公告介绍一项新功能"}]}


def fake_model(prompt, schema):
    if "articles" in schema["properties"]:
        return {"articles": [{"source_id": "S1", "title": "公开功能公告", "summary": "公开公告介绍了一项功能，具体可见原文。", "section": "大模型动态", "evidence": ["公开公告介绍一项新功能"]}]}
    repos = schema["properties"]["projects"]["items"]["properties"]["repo"]["enum"]
    return {"projects": [{"repo": repo, "description": "这个工具用于处理公开数据。功能以仓库说明为准。", "usage": "开发者处理公开数据", "category": "B-开发者工具"} for repo in repos]}


class SourceTests(unittest.TestCase):
    def test_fetch_retries_only_twice_and_never_exposes_raw_error(self):
        with patch("gh_daily.sources._download_once", side_effect=sources.SourceError("来源无法访问")) as request:
            with self.assertRaises(sources.SourceError) as raised:
                sources.fetch("https://example.org")
        self.assertEqual(request.call_count, 2)
        self.assertNotIn("不应暴露", str(raised.exception))

    def test_fetch_rejects_private_and_rebinding_dns_before_connect(self):
        answers = [(2, 1, 6, "", ("8.8.8.8", 443)), (2, 1, 6, "", ("127.0.0.1", 443))]
        with patch.object(sources.socket, "getaddrinfo", return_value=answers), patch.object(sources, "_PinnedHTTPS") as connection:
            with self.assertRaises(sources.SourceError):
                sources.fetch("https://official.example/item")
        connection.assert_not_called()

    def test_fetch_blocks_redirect_to_loopback_without_following(self):
        answers = [(2, 1, 6, "", ("8.8.8.8", 443))]
        with patch.object(sources.socket, "getaddrinfo", return_value=answers), patch.object(sources, "_PinnedHTTPS") as transport:
            response = transport.return_value.getresponse.return_value
            response.status = 302
            response.getheader.return_value = "https://127.0.0.1/private"
            with self.assertRaises(sources.SourceError):
                sources.fetch("https://official.example/redirect")
        self.assertEqual(transport.call_count, 2)
        self.assertTrue(all(call.args[0] == "official.example" and call.args[1] == "8.8.8.8" for call in transport.call_args_list))
        response.read1.assert_not_called()

    def test_fetch_rejects_http_and_embedded_credentials_before_dns(self):
        with patch.object(sources.socket, "getaddrinfo") as lookup:
            for url in ("http://public.example/item", "https://name:password@public.example/item", "https://public.example:8443/item"):
                with self.subTest(url=url), self.assertRaises(sources.SourceError):
                    sources.fetch(url)
        lookup.assert_not_called()

    def test_fetch_pins_public_ip_and_limits_streamed_body(self):
        answers = [(2, 1, 6, "", ("8.8.8.8", 443))]
        with patch.object(sources.socket, "getaddrinfo", return_value=answers), patch.object(sources, "_PinnedHTTPS") as transport:
            response = transport.return_value.getresponse.return_value
            response.status = 200
            response.getheader.return_value = None
            response.read1.side_effect = [b"{\"ok\":true}", b""]
            self.assertEqual(sources.fetch("https://official.example/feed"), '{"ok":true}')
            self.assertEqual(transport.call_args.args[:2], ("official.example", "8.8.8.8"))
            response.read1.side_effect = [b"12345", b"12345"]
            with self.assertRaises(sources.SourceError):
                sources.fetch("https://official.example/feed", max_bytes=4)

    def test_feed_filters_old_future_and_undated_items(self):
        feed = """<rss><channel>
        <item><title>有效公告</title><link>https://openai.com/news/new</link><pubDate>2026-06-01T00:00:00Z</pubDate><description>有效信息</description></item>
        <item><title>旧公告</title><link>https://openai.com/news/old</link><pubDate>2026-05-20T00:00:00Z</pubDate></item>
        <item><title>未来公告</title><link>https://openai.com/news/future</link><pubDate>2026-06-02T00:00:00Z</pubDate></item>
        <item><title>未标日期</title><link>https://openai.com/news/none</link></item>
        </channel></rss>"""
        article = '<meta property="article:published_time" content="2026-06-01T00:00:00Z"><main><h1>有效公告</h1><p>已访问原文的有效信息</p></main>'
        with patch.object(sources, "AI_SOURCES", (("OpenAI", "https://openai.com/feed", "feed"),)), patch.object(sources, "fetch", side_effect=lambda url, **_: feed if url.endswith("/feed") else article):
            result = sources.collect_ai(now=datetime(2026, 6, 1, 1, tzinfo=timezone.utc))
        self.assertEqual([item["title"] for item in result["articles"]], ["有效公告"])
        self.assertTrue(result["articles"][0]["id"].startswith("S"))

    def test_approximate_stars_not_claimed_precise(self):
        self.assertEqual(sources.number("1,234 stars this week"), 1234)
        self.assertEqual(sources.number("+900"), 900)
        self.assertIsNone(sources.number("1.2k"))
        self.assertIsNone(sources.number("暂未获取"))

    def test_empty_trending_fails(self):
        with patch.object(sources, "fetch", return_value="<html>错误页</html>"):
            with self.assertRaises(sources.SourceError):
                sources.collect_trending()

    def test_trending_preserves_real_rank_after_broken_rows(self):
        body = """<article class="Box-row"><h2>损坏的仓库行</h2></article>
        <article class="Box-row"><h2><a href="/sample/second">sample / second</a></h2><a href="/sample/second/stargazers">1234</a></article>"""
        with patch.object(sources, "fetch", return_value=body):
            result = sources.collect_trending()
        self.assertEqual(len(result["projects"]), 1)
        self.assertEqual(result["projects"][0]["rank"], 2)

    def test_search_needs_original_date_and_ignores_other_domains(self):
        search_feed = """<rss><channel>
        <item><title>其它域</title><link>https://elsewhere.example/item</link><pubDate>2026-06-01T00:00:00Z</pubDate></item>
        <item><title>无日期</title><link>https://openai.com/news/undated</link><pubDate>2026-06-01T00:00:00Z</pubDate></item>
        <item><title>原文有日期</title><link>https://openai.com/news/dated</link></item>
        </channel></rss>"""
        def fetch(url, **_):
            if "bing.com" in url:
                return search_feed
            if url.endswith("undated"):
                return "<html><h1>无日期公告</h1></html>"
            if url.endswith("dated"):
                return '<html><head><meta property="article:published_time" content="2026-06-01T00:00:00Z"></head><main><h1>原文日期公告</h1><p>实际内容</p></main></html>'
            raise AssertionError("不应打开域名范围外的地址")
        with patch.object(sources, "fetch", side_effect=fetch):
            rows = sources.search_official("https://openai.com/news", deadline=float("inf"), now=datetime(2026, 6, 1, 1, tzinfo=timezone.utc))
        self.assertEqual([row["url"] for row in rows], ["https://openai.com/news/dated"])

    def test_ai_source_timeout_retains_other_sources(self):
        feed = '<rss><channel><item><title>新公告</title><link>https://openai.com/news/new</link><pubDate>2026-06-01T00:00:00Z</pubDate></item></channel></rss>'
        def fetch(url, **_):
            if url == "https://openai.com/news/new":
                return '<meta property="article:published_time" content="2026-06-01T00:00:00Z"><main><h1>新公告</h1><p>已访问原文的有效信息</p></main>'
            if url.startswith("https://openai.com"):
                return feed
            raise sources.SourceError("来源无法访问")
        with patch.object(sources, "AI_SOURCES", (("失败源", "https://anthropic.com/news", "html"), ("OpenAI", "https://openai.com/feed", "feed"))), patch.object(sources, "fetch", side_effect=fetch):
            result = sources.collect_ai(now=datetime(2026, 6, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(len(result["articles"]), 1)
        self.assertEqual(result["sources"][0]["status"], "failed")
        self.assertEqual(result["sources"][1]["status"], "success")


class ReportTests(unittest.TestCase):
    def test_daily_and_weekly_same_day_are_distinct_and_repeat_is_noop(self):
        project = snapshot()["projects"][0]
        first, changed = reports.archive_text(project, "2026-06-01", False)
        self.assertTrue(changed)
        second, changed = reports.archive_text(project, "2026-06-01", True, first)
        self.assertTrue(changed)
        third, changed = reports.archive_text(project, "2026-06-01", False, second)
        self.assertFalse(changed)
        self.assertEqual(second, third)
        records = reports.archive_records(third)
        self.assertEqual([item["rank"] for item in records], ["#1", "W#1"])
        self.assertIn("**累计上榜**：2 次", third)

    def test_html_escapes_hostile_repository_content(self):
        data = snapshot()
        data["projects"][0]["description"] = '<script>alert("x")</script>'
        result = reports.render_report(data, "2026-06-01")
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)

    def test_explicit_forced_refresh_replaces_same_day_observation_without_new_count(self):
        project = snapshot()["projects"][0]
        text, _ = reports.archive_text(project, "2026-06-01", False)
        newer = {**project, "total": 1500, "growth": 1100}
        updated, changed = reports.archive_text(newer, "2026-06-01", False, text, replace_record=True)
        self.assertTrue(changed)
        records = reports.archive_records(updated)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["total"], 1500)
        self.assertIn("**累计上榜**：1 次", updated)

    def test_ai_unapproved_source_is_rejected(self):
        output = {"articles": [{"source_id": "S-other", "title": "公告", "summary": "无法验证", "section": "大模型动态"}]}
        with patch.object(pipeline, "_generate", return_value=output):
            with self.assertRaises(ValueError):
                pipeline._edit_ai(ai_collection())

    def test_month_uses_daily_only_and_observation_intervals(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = root / "GitHub项目分析"
            library = base / "项目分类库" / "B-开发者工具"
            library.mkdir(parents=True)
            first = snapshot(total=100)
            second = snapshot(total=130)
            (base / "GitHub热点日报_2026-05-02.html").write_text(reports.render_report(first, "2026-05-02"), encoding="utf-8")
            (base / "GitHub热点日报_2026-05-30.html").write_text(reports.render_report(second, "2026-05-30"), encoding="utf-8")
            (base / "GitHub热点周报_2026-W22.html").write_text(reports.render_report(snapshot("weekly", 500), "2026-05-25"), encoding="utf-8")
            archive, _ = reports.archive_text(first["projects"][0], "2026-05-02", False)
            archive, _ = reports.archive_text(second["projects"][0], "2026-05-30", False, archive)
            (library / "sample-project.md").write_text(archive, encoding="utf-8")
            result = reports.aggregate_month(root, "2026-05")
        self.assertEqual(result["days"], ["2026-05-02", "2026-05-30"])
        self.assertEqual(result["projects"][0]["count"], 2)
        self.assertEqual(result["projects"][0]["growth"], 30)
        self.assertEqual(result["new_projects"], ["sample/project"])


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.patches = [patch.object(pipeline, "_today", return_value=date(2026, 6, 1)),
                        patch.object(sources, "collect_ai", side_effect=lambda **_: copy.deepcopy(ai_collection())),
                        patch.object(sources, "collect_trending", side_effect=lambda period, **_: snapshot(period)),
                        patch.object(sources, "enrich_projects", return_value=[]),
                        patch.object(pipeline, "_generate", side_effect=fake_model),
                        patch("gh_daily.build.build_site", side_effect=self.fake_build)]
        for item in self.patches:
            item.start()
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def fake_build(self, root):
        (root / "dist").mkdir(exist_ok=True)
        (root / "dist" / "index.html").write_text("已生成", encoding="utf-8")

    def seed_previous_month(self):
        base = self.root / "GitHub项目分析"
        base.mkdir(exist_ok=True)
        (base / "GitHub热点日报_2026-05-30.html").write_text(reports.render_report(snapshot(), "2026-05-30"), encoding="utf-8")

    def test_monday_month_start_and_successful_repeat_are_idempotent(self):
        self.seed_previous_month()
        first = pipeline.run_update(self.root, "2026-06-01")
        self.assertTrue(first["ok"], first)
        self.assertEqual(first["tasks"]["weekly"]["status"], "success")
        self.assertEqual(first["tasks"]["monthly"]["status"], "success")
        tracked = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file() and ".runtime" not in path.parts}
        with patch.object(sources, "collect_trending", side_effect=AssertionError("重复时不应联网")), patch.object(sources, "collect_ai", side_effect=AssertionError("重复时不应采集")), patch.object(pipeline, "_generate", side_effect=AssertionError("重复时不应调用模型")):
            second = pipeline.run_update(self.root, "2026-06-01")
        self.assertTrue(second["ok"], second)
        self.assertEqual(second["tasks"]["daily"]["status"], "skipped")
        self.assertEqual(second["tasks"]["build"]["status"], "skipped")
        self.assertEqual(tracked, {path: path.read_bytes() for path in tracked})
        archive = next((self.root / "GitHub项目分析" / "项目分类库").rglob("sample-project.md"))
        self.assertEqual(len(reports.archive_records(archive.read_text(encoding="utf-8"))), 2)

    def test_model_failure_keeps_real_trending_and_retries_without_double_count(self):
        self.seed_previous_month()
        with patch.object(pipeline, "_generate", side_effect=ValueError("私密错误绝不能回传")):
            first = pipeline.run_update(self.root, "2026-06-01")
        self.assertFalse(first["ok"])
        self.assertEqual(first["tasks"]["ai"]["status"], "failed")
        self.assertEqual(first["tasks"]["daily"]["status"], "success")
        self.assertNotIn("私密错误", json.dumps(first, ensure_ascii=False))
        with patch.object(sources, "collect_trending", side_effect=AssertionError("已有报告无需重抓榜单")):
            second = pipeline.run_update(self.root, "2026-06-01")
        self.assertTrue(second["ok"], second)
        report = (self.root / "GitHub项目分析" / "GitHub热点日报_2026-06-01.html").read_text(encoding="utf-8")
        self.assertIn("公开功能公告", report)
        archive = next((self.root / "GitHub项目分析" / "项目分类库").rglob("sample-project.md"))
        self.assertEqual(len(reports.archive_records(archive.read_text(encoding="utf-8"))), 2)
        self.assertIn("这个工具用于处理公开数据", archive.read_text(encoding="utf-8"))
        self.assertNotIn("<!-- 项目介绍待补齐 -->", archive.read_text(encoding="utf-8"))

    def test_failed_build_is_retried_even_when_reports_are_idempotent(self):
        self.seed_previous_month()
        (self.root / "dist").mkdir()
        (self.root / "dist" / "index.html").write_text("旧版", encoding="utf-8")
        with patch("gh_daily.build.build_site", side_effect=RuntimeError("构建中断")):
            first = pipeline.run_update(self.root, "2026-06-01")
        self.assertFalse(first["ok"])
        self.assertEqual(first["tasks"]["build"]["status"], "failed")
        self.assertEqual((self.root / "dist" / "index.html").read_text(encoding="utf-8"), "旧版")
        second = pipeline.run_update(self.root, "2026-06-01")
        self.assertTrue(second["ok"], second)
        self.assertEqual(second["tasks"]["daily"]["status"], "skipped")
        self.assertEqual(second["tasks"]["build"]["status"], "success")
        self.assertEqual((self.root / "dist" / "index.html").read_text(encoding="utf-8"), "已生成")
        third = pipeline.run_update(self.root, "2026-06-01")
        self.assertEqual(third["tasks"]["build"]["status"], "skipped")

    def test_missing_runtime_build_state_rebuilds_on_another_machine(self):
        self.seed_previous_month()
        self.assertTrue(pipeline.run_update(self.root, "2026-06-01")["ok"])
        (self.root / ".runtime" / "build-state.json").unlink()
        result = pipeline.run_update(self.root, "2026-06-01")
        self.assertEqual(result["tasks"]["build"]["status"], "success")

    def test_source_failure_does_not_block_weekly_and_monthly(self):
        self.seed_previous_month()
        def collect(period, **_):
            if period == "daily":
                raise sources.SourceError("来源无法访问")
            return snapshot(period)
        with patch.object(sources, "collect_trending", side_effect=collect):
            result = pipeline.run_update(self.root, "2026-06-01")
        self.assertFalse(result["ok"])
        self.assertEqual(result["tasks"]["daily"]["status"], "failed")
        self.assertEqual(result["tasks"]["weekly"]["status"], "success")
        self.assertEqual(result["tasks"]["monthly"]["status"], "success")

    def test_lock_prevents_concurrent_updates(self):
        with pipeline._lock(self.root):
            result = pipeline.run_update(self.root)
        self.assertFalse(result["ok"])
        self.assertIn("lock", result["tasks"])

    def test_no_live_data_backfilled_under_historical_date(self):
        with patch.object(sources, "collect_trending") as trending, patch.object(sources, "collect_ai") as ai:
            result = pipeline.run_update(self.root, "2026-05-29")
        self.assertFalse(result["ok"])
        trending.assert_not_called()
        ai.assert_not_called()


if __name__ == "__main__":
    unittest.main()
