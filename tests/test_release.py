import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from gh_daily.privacy import check_changes, scan_paths


class ReleaseTests(unittest.TestCase):
    def test_tls_trust_store_has_public_roots_without_disabling_verification(self):
        import ssl
        from gh_daily.tls import verified_context
        context = verified_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertGreater(context.cert_store_stats()["x509_ca"], 0)

    def build_fixture(self, root):
        (root / "GitHub项目分析").mkdir()
        (root / "tools").mkdir()
        (root / "web").mkdir()
        (root / "dist").mkdir()
        for name in ["GitHub项目分析/GitHub热点杂志.html", "tools/_杂志数据.json", "content-manifest.json", "dist/index.html"]:
            (root / name).write_text("上一份有效内容", encoding="utf-8")
        return SimpleNamespace(build_db=lambda: ({"issues": [{}], "meta": {}, "generated_at": "2026-10-23"}, [], []), render_html=lambda _: "新的已生成内容")

    def test_rejected_build_does_not_replace_any_published_file(self):
        from gh_daily.build import build_site
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            builder = self.build_fixture(root)
            with patch("gh_daily.build.load_builder", return_value=builder), patch("gh_daily.privacy.scan_paths", return_value=[{"path": "test.md"}]):
                with self.assertRaises(ValueError):
                    build_site(root)
            for name in ["GitHub项目分析/GitHub热点杂志.html", "tools/_杂志数据.json", "content-manifest.json", "dist/index.html"]:
                self.assertEqual((root / name).read_text(), "上一份有效内容")

    def test_failed_publication_rolls_back_source_files_and_site(self):
        from gh_daily.build import build_site, atomic_text
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            builder = self.build_fixture(root)
            failed = False
            def write(path, content):
                nonlocal failed
                if path == root / "tools/_杂志数据.json" and not failed:
                    failed = True
                    raise OSError("模拟写入失败")
                return atomic_text(path, content)
            with patch("gh_daily.build.load_builder", return_value=builder), patch("gh_daily.privacy.scan_paths", return_value=[]), patch("gh_daily.build.atomic_text", side_effect=write):
                with self.assertRaises(OSError):
                    build_site(root)
            for name in ["GitHub项目分析/GitHub热点杂志.html", "tools/_杂志数据.json", "content-manifest.json", "dist/index.html"]:
                self.assertEqual((root / name).read_text(), "上一份有效内容")

    def test_site_build_rejects_nested_cache_names_and_unknown_attachments(self):
        from gh_daily.build import build_site
        for name, content in [("build/private.md", "/" + "Users/test-person/private"), ("private.backup", "未批准附件")]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                builder = self.build_fixture(root)
                extra = root / "web" / name
                extra.parent.mkdir(parents=True, exist_ok=True)
                extra.write_text(content, encoding="utf-8")
                with patch("gh_daily.build.load_builder", return_value=builder):
                    with self.assertRaises(ValueError):
                        build_site(root)
                self.assertEqual((root / "dist/index.html").read_text(), "上一份有效内容")

    def test_direct_dist_scan_never_skips_build_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "dist"
            file = root / "build/private.md"
            file.parent.mkdir(parents=True)
            file.write_text("/" + "Users/test-person/private", encoding="utf-8")
            self.assertTrue(scan_paths(root))

    def test_private_paths_report_rule_without_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "README.md").write_text("/" + "Users/hidden-person/private", encoding="utf-8")
            findings = scan_paths(path)
            self.assertEqual(findings[0]["rule"], "本机用户路径")
            self.assertNotIn("hidden-person", json.dumps(findings))

    def test_commit_allowlist_rejects_configuration_and_code(self):
        root = Path(".")
        paths = ["GitHub项目分析/GitHub热点日报_2026-01-01.html", "AI前沿资讯/日报/2026-01-01-AI日报.md", "dist/pwa.js", "gh_daily/config.py", ".env", "dist/../.env"]
        self.assertEqual(check_changes(root, paths), paths[3:])

    def test_public_website_home_path_is_not_a_private_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("https://news.example.com/news/home/123/report", encoding="utf-8")
            self.assertEqual(scan_paths(root), [])

    def test_nested_cache_named_directory_does_not_bypass_scanning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / "dist/build/private.md"
            file.parent.mkdir(parents=True)
            file.write_text("/" + "Users/private-person/document", encoding="utf-8")
            self.assertTrue(scan_paths(root, public_release=True))
            (root / "docs").mkdir()
            (root / "docs/private.backup").write_text("不可自动批准的附件", encoding="utf-8")
            self.assertTrue(any(f["rule"] == "未允许的文件类型" for f in scan_paths(root, public_release=True)))

    def test_symbolic_link_is_not_public(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "README.md"
            target.write_text("公开内容", encoding="utf-8")
            try:
                (root / "alias.md").symlink_to(target)
            except OSError:
                self.skipTest("系统未启用符号链接")
            self.assertTrue(any(f["rule"] == "符号链接" for f in scan_paths(root)))

    def test_manifest_files_match_built_site(self):
        root = Path(__file__).resolve().parent.parent
        manifest_file = root / "content-manifest.json"
        if not manifest_file.exists():
            self.skipTest("首次构建后验证清单")
        manifest = json.loads(manifest_file.read_text())
        for entry in manifest["files"]:
            path = root / "dist" / entry["path"]
            self.assertEqual(path.stat().st_size, entry["size"], entry["path"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry["sha256"], entry["path"])


if __name__ == "__main__":
    unittest.main()
