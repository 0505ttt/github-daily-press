"""现有 AI 工具采编与公开发布的边界回归。"""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gh_daily.publishing import PublishError, _check_outgoing, _public_text, import_content


class PublishingTests(unittest.TestCase):
    def test_redaction_preserves_real_web_source_and_removes_active_html(self):
        original = '<a href="https://news.example.com/news/home/12">来源</a><script>坏脚本</script><p onclick="bad()">/' + 'Users/private-person/note</p><a href="javascript:bad()">坏链接</a>'
        public = _public_text(original, html=True)
        self.assertIn('https://news.example.com/news/home/12', public)
        self.assertNotIn('private-person', public)
        self.assertNotIn('<script', public)
        self.assertNotIn('onclick', public)
        self.assertNotIn('javascript:', public)

    def test_import_strips_svg_mathml_and_alternate_url_attributes(self):
        hostile = '<svg xmlns:xlink="http://www.w3.org/1999/xlink"><a xlink:href="javascript:alert(1)"><text>坏链接</text></a></svg><math><annotation-xml encoding="text/html"><script>坏脚本</script></annotation-xml></math><p><a xlink:href="javascript:bad()" ping="https://tracker.example/">保留文字</a></p>'
        public = _public_text(hostile, html=True)
        self.assertNotIn('<svg', public)
        self.assertNotIn('<math', public)
        self.assertNotIn('xlink', public)
        self.assertNotIn('javascript:', public)
        self.assertNotIn('ping=', public)
        self.assertIn('保留文字', public)

    def test_import_rejects_secret_before_touching_public_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root, source = Path(directory) / 'public', Path(directory) / 'source'
            root.mkdir()
            (source / 'AI前沿资讯/日报').mkdir(parents=True)
            (source / 'GitHub项目分析').mkdir()
            (source / 'AI前沿资讯/日报/2026-10-23-AI日报.md').write_text('sk-' + 'x' * 30, encoding='utf-8')
            with patch('gh_daily.publishing.load_builder'):
                with self.assertRaises(PublishError):
                    import_content(root, source)
            self.assertFalse((root / 'AI前沿资讯').exists())

    def test_import_rollback_on_failed_build_and_ignores_source_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root, source = Path(directory) / 'public', Path(directory) / 'source'
            for base in (root, source):
                (base / 'AI前沿资讯/日报').mkdir(parents=True)
                (base / 'GitHub项目分析').mkdir()
            destination = root / 'AI前沿资讯/日报/2026-10-23-AI日报.md'
            destination.write_text('旧的有效内容', encoding='utf-8')
            (source / 'AI前沿资讯/日报/2026-10-23-AI日报.md').write_text('新资料', encoding='utf-8')
            (source / 'private.py').write_text('不能导入', encoding='utf-8')
            with patch('gh_daily.publishing.load_builder'), patch('gh_daily.publishing.build_site', side_effect=ValueError('模拟失败')):
                with self.assertRaises(ValueError):
                    import_content(root, source)
            self.assertEqual(destination.read_text(encoding='utf-8'), '旧的有效内容')
            self.assertFalse((root / 'private.py').exists())

    def test_import_repeat_does_not_create_extra_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root, source = Path(directory) / 'public', Path(directory) / 'source'
            root.mkdir()
            (source / 'AI前沿资讯/日报').mkdir(parents=True)
            (source / 'GitHub项目分析').mkdir()
            (source / 'AI前沿资讯/日报/2026-10-23-AI日报.md').write_text('真实资料', encoding='utf-8')
            with patch('gh_daily.publishing.load_builder'), patch('gh_daily.publishing.build_site', return_value={'revision': 'valid'}):
                self.assertEqual(import_content(root, source)['changed'], 1)
                self.assertEqual(import_content(root, source)['changed'], 0)

    def test_outgoing_history_checks_each_commit_not_only_head(self):
        def git(root, *args, **kwargs):
            output = b''
            if args[0] == 'rev-list':
                output = b'' if '--merges' in args else b'first\nsecond\n'
            elif args[0] == 'diff-tree':
                output = 'AI前沿资讯/日报/2026-10-23-AI日报.md\0'.encode()
            elif args[0] == 'show':
                output = (('sk-' + 'x' * 30) if args[1].startswith('first:') else '安全的最终内容').encode()
            return subprocess.CompletedProcess(args, 0, output, b'')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.runtime').mkdir()
            with patch('gh_daily.publishing._git', side_effect=git):
                with self.assertRaises(PublishError):
                    _check_outgoing(root)

    def test_outgoing_merge_is_rejected_before_diff(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('gh_daily.publishing._git', return_value=subprocess.CompletedProcess([], 0, b'merge-commit\n', b'')) as git:
                with self.assertRaises(PublishError):
                    _check_outgoing(root)
            self.assertEqual(git.call_count, 1)


if __name__ == '__main__':
    unittest.main()
