"""桌面种子完整性、用户内容保留和服务生命周期回归。"""

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gh_daily import __version__
from gh_daily.desktop import DesktopError, bundled_payload, desktop_directory, main, prepare_workspace, run_window, seed_manifest


class DesktopTests(unittest.TestCase):
    def payload(self, base, changes=None):
        payload = base / "payload"
        payload.mkdir(exist_ok=True)
        files = {"dist/index.html": "<!doctype html><title>尚无自己的日报</title>",
                 "tools/build_magazine.py": "# 构建脚本\n", "web/app.css": "body{}"}
        files.update(changes or {})
        entries = []
        for name, text in files.items():
            target = payload / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            data = target.read_bytes()
            entries.append({"path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        revision = hashlib.sha256(json.dumps(entries).encode()).hexdigest()
        (payload / "desktop-seed.json").write_text(json.dumps({"version": __version__, "mode": "empty-local", "revision": revision,
                                                               "files": entries}), encoding="utf-8")
        return payload

    def test_first_launch_has_empty_reading_without_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = prepare_workspace(self.payload(base), base / "user")
            self.assertIn("尚无自己的日报", (root / "dist/index.html").read_text(encoding="utf-8"))
            self.assertFalse((root / "GitHub项目分析").exists())
            self.assertEqual(root, prepare_workspace(base / "payload", base / "user"))

    def test_tampered_seed_is_rejected_before_workspace_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            payload = self.payload(base)
            (payload / "dist/index.html").write_text("被改写", encoding="utf-8")
            with self.assertRaises(DesktopError):
                prepare_workspace(payload, base / "user")
            self.assertFalse((base / "user").exists())

    def test_upgrade_updates_program_and_preserves_user_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = prepare_workspace(self.payload(base), base / "user")
            report = root / "GitHub项目分析/日报.html"
            report.parent.mkdir()
            report.write_text("用户修订", encoding="utf-8")
            payload = self.payload(base, {"web/app.css": "body{color:green}"})
            with patch("gh_daily.build.build_site") as build:
                prepare_workspace(payload, base / "user")
                build.assert_called_once_with(root, allow_empty=True)
            self.assertEqual(report.read_text(encoding="utf-8"), "用户修订")
            self.assertEqual((root / "web/app.css").read_text(encoding="utf-8"), "body{color:green}")

    def test_seed_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            payload = self.payload(base)
            manifest = json.loads((payload / "desktop-seed.json").read_text(encoding="utf-8"))
            manifest["files"][0]["path"] = "../private.json"
            (payload / "desktop-seed.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(DesktopError):
                seed_manifest(payload)

    def test_frozen_resource_root_resolves_packager_link(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            payload = self.payload(base)
            try:
                (base / "desktop_payload").symlink_to(payload, target_is_directory=True)
            except OSError:
                self.skipTest("当前系统不允许创建符号链接")
            with patch("gh_daily.desktop.sys.frozen", True, create=True), \
                    patch("gh_daily.desktop.sys._MEIPASS", base, create=True):
                self.assertEqual(bundled_payload(), payload.resolve())

    def test_window_failure_stops_its_server(self):
        server = Mock(origin="http://127.0.0.1:8765")
        webview = Mock()
        webview.settings = {}
        webview.start.side_effect = RuntimeError("浏览引擎未启动")
        with tempfile.TemporaryDirectory() as temporary:
            with patch("gh_daily.desktop.LocalServer", return_value=server), \
                    patch("gh_daily.desktop.threading.Thread"), patch.dict("sys.modules", {"webview": webview}):
                with self.assertRaises(RuntimeError):
                    run_window(Path(temporary), Path(temporary) / "storage")
        server.shutdown.assert_called_once()
        server.server_close.assert_called_once()
        self.assertEqual(webview.create_window.call_args.args[1], "http://127.0.0.1:8765/")
        self.assertIsNone(webview.create_window.call_args.kwargs.get("js_api"))

    def test_port_conflict_does_not_open_another_server(self):
        with patch("gh_daily.desktop.LocalServer", side_effect=OSError):
            with self.assertRaisesRegex(DesktopError, "8765"):
                run_window(Path("."), Path("."))

    def test_first_desktop_launch_does_not_create_author_sync_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            payload = self.payload(base)
            with patch("gh_daily.desktop.bundled_payload", return_value=payload), \
                    patch("gh_daily.desktop.desktop_directory", return_value=base / "user"), \
                    patch("gh_daily.desktop.run_window") as window, \
                    patch.dict("os.environ", {"GH_DAILY_CONFIG_DIR": str(base / "config")}):
                self.assertEqual(main([]), 0)
            window.assert_called_once()
            self.assertFalse((base / "config/config.json").exists())

    def test_desktop_data_override_matches_persistent_local_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict("os.environ", {"GH_DAILY_DATA_DIR": temporary}):
                self.assertEqual(desktop_directory(), Path(temporary).resolve())

    def test_real_empty_seed_first_report_and_restart_preserve_own_issue_one(self):
        from gh_daily.build import build_site, load_builder
        from gh_daily.reports import render_report
        from tools.package_desktop import prepare_payload

        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            (source / "tools").mkdir(parents=True)
            shutil.copyfile(project / "tools/build_magazine.py", source / "tools/build_magazine.py")
            shutil.copytree(project / "web", source / "web")
            # 模拟仓库中存在的历史；桌面备料必须完全忽略它，也不复制原 dist。
            (source / "GitHub项目分析").mkdir()
            (source / "GitHub项目分析/GitHub热点日报_2025-01-01.html").write_text("不得带入的历史", encoding="utf-8")
            (source / "dist").mkdir()
            (source / "dist/index.html").write_text("不得带入的内嵌历史", encoding="utf-8")
            with patch("tools.package_desktop.license_texts", return_value="第三方许可测试文本"):
                payload = prepare_payload(source, base / "package")
            root = prepare_workspace(payload, base / "user")
            db, _, _ = load_builder(root).build_db()
            self.assertEqual(db["issues"], [])
            self.assertEqual(db["projects"], {})
            self.assertFalse(db["ai_days"])
            self.assertFalse(any(root.rglob("GitHub热点日报_*.html")))
            self.assertNotIn("不得带入", (root / "dist/GitHub项目分析/GitHub热点杂志.html").read_text(encoding="utf-8"))
            snapshot = {"period": "daily", "source": "https://github.com/trending?since=daily",
                        "fetched_at": "2026-06-01T00:30:00+00:00", "projects": [
                            {"repo": "sample/project", "url": "https://github.com/sample/project", "rank": 1,
                             "description": "测试夹具", "total": 1200, "growth": 100, "lang": "Python",
                             "category": "B-开发者工具", "usage": "测试"}]}
            report = root / "GitHub项目分析/GitHub热点日报_2026-06-01.html"
            report.write_text(render_report(snapshot, "2026-06-01"), encoding="utf-8")
            build_site(root)
            first = load_builder(root).build_db()[0]
            self.assertEqual(first["meta"]["count_daily"], 1)
            self.assertEqual(first["issues"][0]["issue"], 1)
            restarted = prepare_workspace(payload, base / "user")
            after = load_builder(restarted).build_db()[0]
            self.assertEqual(after["issues"], first["issues"])
            self.assertEqual(after["meta"]["count_daily"], 1)
            (root / "GitHub项目分析/GitHub热点日报_2026-06-02.html").write_text(
                render_report(snapshot, "2026-06-02"), encoding="utf-8")
            build_site(root)
            # 新包仍然是空种子；升级也不能重置自己的期数。
            stylesheet = source / "web/app.css"
            stylesheet.write_text(stylesheet.read_text(encoding="utf-8") + "\n/* 升级夹具 */", encoding="utf-8")
            with patch("tools.package_desktop.license_texts", return_value="第三方许可测试文本"):
                updated_payload = prepare_payload(source, base / "package")
            upgraded = prepare_workspace(updated_payload, base / "user")
            accumulated = load_builder(upgraded).build_db()[0]
            self.assertEqual([issue["issue"] for issue in accumulated["issues"]], [1, 2])
            self.assertEqual(accumulated["meta"]["count_daily"], 2)
