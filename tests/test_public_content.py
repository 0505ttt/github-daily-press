"""报告运行注记不得随导入或构建公开；正文中的产品名称应保留。"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gh_daily.privacy import scan_paths
from gh_daily.public_content import contains_editorial_trace, sanitize_embedded_content, sanitize_structured_content
from gh_daily.publishing import PublishError, _public_text, import_content


class PublicContentTests(unittest.TestCase):
    def test_report_footer_removes_task_and_split_tool_byline_keeps_source(self):
        original = '<footer>数据来自 <a href="https://example.org/news">官方公告</a> · 由「虚构晨间简报」私人采编任务生成 · 由 <b>Example Assistant</b> 自动生成</footer>'
        public = _public_text(original, html=True)
        self.assertNotIn('虚构晨间简报', public)
        self.assertNotIn('Example Assistant', public)
        self.assertIn('https://example.org/news', public)
        self.assertIn('官方公告', public)
        self.assertFalse(contains_editorial_trace(public, html=True))
        self.assertEqual(public, _public_text(public, html=True))

    def test_snapshot_keeps_date_and_url_without_running_history(self):
        original = '<p>本报告据 2025-02-02 01:46 UTC 快照整理，与当日 05:45 自动任务的榜单相近。</p><footer>补档说明：2025-02-02 的原日报因任务未启动未生成，本文件由 2025-02-02 01:46 UTC 的快照重建（https://web.archive.org/web/20250202014600/https://github.com/trending）。</footer>'
        public = _public_text(original, html=True)
        self.assertNotIn('05:45', public)
        self.assertNotIn('任务未启动', public)
        self.assertIn('2025-02-02 01:46 UTC', public)
        self.assertIn('https://web.archive.org/web/20250202014600/', public)
        self.assertIn('不代表整日完整榜单', public)

    def test_news_tools_remain_but_private_publication_relationship_does_not(self):
        original = 'Hermes、ZCode 和 Example Assistant 是文章介绍的工具。\n项目可以自动生成文档。对读者而言——正是驱动「虚构科技日报」的 Example Assistant 的核心。\n> 本报告由 Example Assistant 自动生成 | 数据截至 2025-02-02\n'
        public = _public_text(original, html=False)
        self.assertIn('Hermes、ZCode 和 Example Assistant 是文章介绍的工具', public)
        self.assertIn('项目可以自动生成文档', public)
        self.assertNotIn('虚构科技日报', public)
        self.assertNotIn('个人工作机', public)
        self.assertIn('数据截至 2025-02-02', public)
        self.assertEqual(public, _public_text(public, html=False))
        news = '项目的「Agentic Infrastructure」组合可以执行复杂的长时任务。'
        self.assertEqual(_public_text(news, html=False), news)
        self.assertFalse(contains_editorial_trace(news))

    def test_private_html_comments_and_author_metadata_are_removed(self):
        public = _public_text('<meta name="author" content="某位部署者"><!-- 内部运行备注：私人任务 --><p>公开文章</p>', html=True)
        self.assertNotIn('某位部署者', public)
        self.assertNotIn('私人任务', public)
        self.assertIn('公开文章', public)

    def test_footer_variants_keep_collection_date_and_snapshot_timestamp(self):
        for class_name in ('foot', 'foot-note', 'table-end', 'meta'):
            original = f'<div class="{class_name}">抓取时间 2025-02-02 05:45 CST · 由 Example Assistant 自动生成</div>'
            public = _public_text(original, html=True)
            self.assertIn('2025-02-02', public)
            self.assertNotIn('05:45', public)
            self.assertNotIn('Example Assistant', public)
        snapshot = '<div class="footer-note">快照时间：2025-02-02 05:45 UTC</div>'
        self.assertIn('2025-02-02 05:45 UTC', _public_text(snapshot, html=True))

    def test_scanner_flags_editorial_trace_in_content_not_tutorial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'GitHub项目分析').mkdir()
            (root / 'docs').mkdir()
            sample = '<footer>由「虚构日刊」私人采编任务生成</footer>'
            (root / 'GitHub项目分析/日报.html').write_text(sample, encoding='utf-8')
            (root / 'docs/教程.md').write_text(sample, encoding='utf-8')
            findings = scan_paths(root)
            self.assertEqual(findings, [{'path': 'GitHub项目分析/日报.html', 'rule': '私人采编注记'}])
        embedded = '<script>const DATA={"note":"原日报因任务未启动未生成"};</script>'
        self.assertTrue(contains_editorial_trace(embedded, html=True))

    def test_repeated_import_does_not_restore_private_notes_or_overwrite_public_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root, source = Path(directory) / 'public', Path(directory) / 'source'
            root.mkdir()
            (source / 'AI前沿资讯/日报').mkdir(parents=True)
            (source / 'GitHub项目分析').mkdir()
            (root / '补档说明.md').write_text('公开快照政策', encoding='utf-8')
            (source / '补档说明.md').write_text('内部运行备注：私人工作机', encoding='utf-8')
            (source / 'AI前沿资讯/日报/2025-02-02-AI日报.md').write_text('公开新闻\n> 本报告由 Example Assistant 自动生成\n', encoding='utf-8')
            with patch('gh_daily.publishing.load_builder'), patch('gh_daily.publishing.build_site', return_value={'revision': 'valid'}):
                self.assertEqual(import_content(root, source)['changed'], 1)
                self.assertEqual(import_content(root, source)['changed'], 0)
            public = (root / 'AI前沿资讯/日报/2025-02-02-AI日报.md').read_text(encoding='utf-8')
            self.assertNotIn('Example Assistant', public)
            self.assertNotIn('私人工作机', public)
            self.assertEqual((root / '补档说明.md').read_text(encoding='utf-8'), '公开快照政策')

    def test_secret_in_removed_note_still_rejects_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root, source = Path(directory) / 'public', Path(directory) / 'source'
            root.mkdir()
            (source / 'AI前沿资讯/日报').mkdir(parents=True)
            (source / 'GitHub项目分析').mkdir()
            (source / 'AI前沿资讯/日报/2025-02-02-AI日报.md').write_text('内部运行备注：sk-' + 'x' * 30, encoding='utf-8')
            with patch('gh_daily.publishing.load_builder'):
                with self.assertRaisesRegex(PublishError, '疑似凭据'):
                    import_content(root, source)
            self.assertFalse((root / 'AI前沿资讯').exists())

    def test_import_preserves_newline_bytes_and_is_idempotent_with_windows_text_io(self):
        native_fdopen = os.fdopen

        def windows_fdopen(fd, mode='r', *args, **kwargs):
            if 'b' not in mode:
                kwargs.setdefault('newline', '\r\n')
            return native_fdopen(fd, mode, *args, **kwargs)

        for newline in ('\n', '\r\n'):
            with self.subTest(newline=repr(newline)), tempfile.TemporaryDirectory() as directory:
                root, source = Path(directory) / 'public', Path(directory) / 'source'
                root.mkdir()
                (source / 'AI前沿资讯/日报').mkdir(parents=True)
                (source / 'GitHub项目分析').mkdir()
                relative = 'AI前沿资讯/日报/2025-02-02-AI日报.md'
                content = ('公开新闻' + newline + '第二条报道' + newline).encode('utf-8')
                (source / relative).write_bytes(content)
                with patch('gh_daily.publishing.os.fdopen', side_effect=windows_fdopen), \
                        patch('gh_daily.publishing.load_builder'), \
                        patch('gh_daily.publishing.build_site', return_value={'revision': 'valid'}):
                    self.assertEqual(import_content(root, source)['changed'], 1)
                    self.assertEqual((root / relative).read_bytes(), content)
                    self.assertEqual(import_content(root, source)['changed'], 0)
                    self.assertEqual((root / relative).read_bytes(), content)
                    (source / relative).write_bytes(content + '新增报道'.encode('utf-8'))
                    with patch('gh_daily.publishing.build_site', side_effect=ValueError('模拟构建失败')):
                        with self.assertRaisesRegex(ValueError, '模拟构建失败'):
                            import_content(root, source)
                    self.assertEqual((root / relative).read_bytes(), content)

    def test_split_html_and_multiline_markdown_notes_reject_whole_content(self):
        samples = [
            ('<p>内部运行备注：<b>虚构私人任务甲</b>每天07:00执行。</p><p>公开文章</p>', True),
            ('<p><b>内部运行备注：</b>虚构私人任务甲每天07:00执行。</p>', True),
            ('<p>内部<span>运行</span>备注：虚构私人任务甲</p>', True),
            ('内部运行备注：\n  虚构私人任务甲每天07:00执行。\n\n公开文章', False),
        ]
        for original, html in samples:
            with self.subTest(html=html, original=original):
                self.assertTrue(contains_editorial_trace(original, html=html))
                with self.assertRaisesRegex(PublishError, '私人运行注记') as context:
                    _public_text(original, html=html)
                self.assertNotIn('虚构私人任务甲', str(context.exception))

    def test_private_note_rejection_keeps_existing_public_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root, source = Path(directory) / 'public', Path(directory) / 'source'
            for base in (root, source):
                (base / 'AI前沿资讯/日报').mkdir(parents=True)
                (base / 'GitHub项目分析').mkdir()
            relative = 'AI前沿资讯/日报/2025-02-02-AI日报.md'
            (root / relative).write_text('旧的公开文章', encoding='utf-8')
            (source / relative).write_text('内部运行备注：\n  虚构私人任务甲\n\n新的公开文章', encoding='utf-8')
            with patch('gh_daily.publishing.load_builder'), patch('gh_daily.publishing.build_site') as build:
                with self.assertRaisesRegex(PublishError, '私人运行注记'):
                    import_content(root, source)
                build.assert_not_called()
            self.assertEqual((root / relative).read_text(encoding='utf-8'), '旧的公开文章')

    def test_structured_and_embedded_data_preserve_snapshot_url_and_product_description(self):
        original = {
            'snapshot': '2025-02-02 05:45 UTC',
            'date': '2025-02-02 05:45 CST',
            'snapshot_url': 'https://web.archive.org/web/20250202054500/https://github.com/trending',
            'description': '由 Example Generator 自动生成项目文档，支持 </script> 等代码片段。',
            'wind': '本报告据快照整理，与当日 05:45 采编任务的榜单一致。',
            'entries': [{'desc': '基于公开项目材料。正是驱动「虚构科技日报」的 Example Assistant 的核心。'}],
        }
        cleaned = sanitize_structured_content(original)
        for key in ('snapshot', 'date', 'snapshot_url', 'description'):
            self.assertEqual(cleaned[key], original[key])
        self.assertNotIn('采编任务', cleaned['wind'])
        self.assertNotIn('虚构科技日报', cleaned['entries'][0]['desc'])
        encoded = json.dumps(original, ensure_ascii=False).replace('</', '<\\/')
        html = '<script>const DB=' + encoded + ';const untouched="样例";</script>'
        result = sanitize_embedded_content(html)
        parsed, _ = json.JSONDecoder().raw_decode(result.split('const DB=', 1)[1])
        self.assertEqual(parsed, cleaned)
        self.assertEqual(result, sanitize_embedded_content(result))
        self.assertTrue(result.endswith(';const untouched="样例";</script>'))
        self.assertNotIn('</script> 等代码', result)
        html_block = '<script type="application/json" id="DB">' + encoded + '</script><script>var DB=JSON.parse(document.getElementById("DB").textContent);</script>'
        block_result = sanitize_embedded_content(html_block)
        block_data = block_result.split('id="DB">', 1)[1].split('</script>', 1)[0]
        self.assertEqual(json.loads(block_data), cleaned)
        self.assertEqual(block_result, sanitize_embedded_content(block_result))
        self.assertTrue(block_result.endswith('<script>var DB=JSON.parse(document.getElementById("DB").textContent);</script>'))
        plain_description = '由 Example Generator 自动生成项目文档。'
        self.assertEqual(_public_text(plain_description, html=False), plain_description)


if __name__ == '__main__':
    unittest.main()
