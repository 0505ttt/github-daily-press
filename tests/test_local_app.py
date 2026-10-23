"""本地应用的安全边界与离线协议回归。"""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from gh_daily import config, models, sync
from gh_daily.server import LocalServer


class LocalAppTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.environment = patch.dict(os.environ, {"GH_DAILY_CONFIG_DIR": str(self.root / "private")})
        self.environment.start()
        self.old = {name: os.environ.pop(name) for name in config.ENVIRONMENT.values() if name in os.environ}
        (self.root / "dist").mkdir()
        (self.root / "dist" / "index.html").write_text("<h1>公开阅读</h1>", encoding="utf-8")
        self.server = None

    def tearDown(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        os.environ.update(self.old)
        self.environment.stop()
        self.temporary.cleanup()

    def start(self):
        self.server = LocalServer(("127.0.0.1", 0), self.root)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self.server.server_address[1]

    def request(self, method, path, value=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=3)
        selected = dict(headers or {})
        if value is not None:
            selected.setdefault("Content-Type", "application/json")
        connection.request(method, path, None if value is None else json.dumps(value), selected)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_config_never_echoes_key_and_blank_preserves(self):
        with patch("gh_daily.config.os.chmod", wraps=os.chmod) as chmod:
            public = config.save_config({"api_key": "test-only-placeholder", "model": "example-model"})
        chmod.assert_any_call(self.root / "private", 0o700)
        self.assertTrue(any(call.args[1] == 0o600 for call in chmod.call_args_list))
        self.assertTrue(public["api_key_set"])
        self.assertNotIn("api_key", public)
        config.save_config({"api_key": "", "max_tokens": 1024})
        self.assertEqual(config.load_config()["api_key"], "test-only-placeholder")
        # Windows 的 chmod 只控制只读位，不能用 POSIX mode 核验其用户 ACL。
        if os.name == "posix":
            self.assertEqual((self.root / "private/config.json").stat().st_mode & 0o777, 0o600)
        config.save_config({"clear_api_key": True})
        self.assertFalse(config.public_config()["api_key_set"])

    def test_config_environment_overrides_without_persisting(self):
        with patch.dict(os.environ, {"GH_DAILY_API_KEY": "environment-placeholder"}):
            config.save_config({"model": "demo"})
            self.assertEqual(config.load_config()["api_key"], "environment-placeholder")
            self.assertNotIn("environment-placeholder", (self.root / "private/config.json").read_text(encoding="utf-8"))

    def test_key_is_cleared_when_endpoint_changes_without_new_key(self):
        base = config.prepare_config({"api_key": "old-placeholder"})
        for changed in ({"base_url": "https://other.example/v1"},
                        {"base_url": "https://other.example/v1", "api_key": ""},
                        {"base_url": "https://api.openai.com/v2", "api_key": "   "},
                        {"provider": "ollama", "base_url": "http://127.0.0.1:11434"}):
            with self.subTest(changed=changed):
                self.assertEqual(config.prepare_config(changed, base)["api_key"], "")
        changed = {"base_url": "https://other.example/v1", "api_key": "new-placeholder"}
        self.assertEqual(config.prepare_config(changed, base)["api_key"], "new-placeholder")
        config.save_config({"api_key": "old-placeholder"})
        config.save_config({"base_url": "https://other.example/v1"})
        self.assertEqual(config.load_config()["api_key"], "")
        self.start()
        config.save_config({"api_key": "old-placeholder"})
        headers = {"Origin": self.server.origin, "X-GH-Daily-Token": self.server.token}
        with patch("gh_daily.server.test_connection", return_value={"ok": True}) as connection:
            status, _, _ = self.request("POST", "/api/test-connection",
                                        {"base_url": "https://new.example/v1", "api_key": ""}, headers)
            self.assertEqual(status, 200)
            self.assertEqual(connection.call_args.args[0]["api_key"], "")

    def test_same_normalized_endpoint_preserves_key(self):
        base = config.prepare_config({"api_key": "old-placeholder"})
        for value in ("https://api.openai.com/v1", "HTTPS://API.OPENAI.COM:443/v1/", "https://api.openai.com/v1///"):
            with self.subTest(value=value):
                result = config.prepare_config({"base_url": value, "api_key": ""}, base)
                self.assertEqual(result["api_key"], "old-placeholder")
                self.assertEqual(result["base_url"], "https://api.openai.com/v1")

    def test_stored_and_environment_endpoint_keys_remain_bound(self):
        config.save_config({"base_url": "https://stored.example/v1", "api_key": "stored-placeholder"})
        self.assertEqual(config.load_config()["api_key"], "stored-placeholder")
        with patch.dict(os.environ, {"GH_DAILY_MODEL": "different-model"}):
            self.assertEqual(config.load_config()["api_key"], "stored-placeholder")
        with patch.dict(os.environ, {"GH_DAILY_BASE_URL": "https://new.example/v1"}):
            self.assertEqual(config.load_config()["api_key"], "")
        with patch.dict(os.environ, {"GH_DAILY_BASE_URL": "https://new.example/v1", "GH_DAILY_API_KEY": "new-placeholder"}):
            self.assertEqual(config.load_config()["api_key"], "new-placeholder")
        with patch.dict(os.environ, {"GH_DAILY_PROVIDER": "ollama", "GH_DAILY_BASE_URL": "http://127.0.0.1:11434", "GH_DAILY_API_KEY": "ollama-placeholder"}):
            self.assertEqual(config.load_config()["api_key"], "ollama-placeholder")

    def test_environment_key_alone_prevents_saved_endpoint_change(self):
        with patch.dict(os.environ, {"GH_DAILY_API_KEY": "environment-placeholder"}):
            for update in ({"base_url": "https://different.example/v1"},
                           {"provider": "ollama", "base_url": "http://127.0.0.1:11434"}):
                with self.subTest(update=update), self.assertRaisesRegex(config.ConfigError, "环境变量"):
                    config.save_config(update)
            self.assertEqual(config.load_config()["base_url"], config.DEFAULTS["base_url"])
            self.assertFalse((self.root / "private/config.json").exists())

    def test_environment_key_prevents_endpoint_change_even_with_new_payload_key(self):
        with patch.dict(os.environ, {"GH_DAILY_API_KEY": "environment-placeholder"}):
            with self.assertRaisesRegex(config.ConfigError, "环境变量"):
                config.save_config({"base_url": "https://different.example/v1", "api_key": "new-placeholder"})
            self.assertEqual(config.load_config()["api_key"], "environment-placeholder")
            self.assertFalse((self.root / "private/config.json").exists())

    def test_environment_key_allows_same_endpoint_nonsecret_settings(self):
        with patch.dict(os.environ, {"GH_DAILY_API_KEY": "environment-placeholder"}):
            public = config.save_config({"base_url": "HTTPS://API.OPENAI.COM:443/v1/",
                                         "source_repo": "example/project", "model": "demo", "timeout": 30})
            self.assertEqual(public["source_repo"], "example/project")
            self.assertEqual(public["timeout"], 30)
            self.assertEqual(config.load_config()["api_key"], "environment-placeholder")
            self.assertNotIn("environment-placeholder", (self.root / "private/config.json").read_text(encoding="utf-8"))

    def test_provider_and_limits_validation(self):
        for patch_value in ({"base_url": "http://example.com/v1"}, {"base_url": "https://user:pass@example.com/v1"},
                            {"timeout": True}, {"timeout": 121}, {"provider": "ollama", "base_url": "http://192.168.1.1:11434"}):
            with self.subTest(patch_value=patch_value), self.assertRaises(config.ConfigError):
                config.prepare_config(patch_value)
        self.assertEqual(config.prepare_config({"provider": "ollama", "base_url": "http://127.0.0.1:11434"})["provider"], "ollama")

    def test_api_requires_exact_host_origin_and_token(self):
        self.start()
        status, headers, _ = self.request("GET", "/api/config", headers={"Host": "attacker.example"})
        self.assertEqual(status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        status, _, _ = self.request("POST", "/api/config", {"model": "demo"})
        self.assertEqual(status, 403)
        _, headers, body = self.request("GET", "/api/session")
        token = json.loads(body)["token"]
        self.assertEqual(headers["Cache-Control"], "no-store")
        accepted = {"Origin": self.server.origin, "X-GH-Daily-Token": token}
        status, _, body = self.request("POST", "/api/config", {"api_key": "test-only-placeholder"}, accepted)
        self.assertEqual(status, 200)
        self.assertNotIn(b"test-only-placeholder", body)
        accepted["Origin"] = "https://attacker.example"
        self.assertEqual(self.request("POST", "/api/config", {}, accepted)[0], 403)

    def test_static_service_rejects_hidden_traversal_and_symlinks(self):
        (self.root / "secret.txt").write_text("private", encoding="utf-8")
        (self.root / "dist" / "exposed.txt").symlink_to(self.root / "secret.txt")
        self.start()
        self.assertEqual(self.request("GET", "/")[0], 200)
        for path in ("/secret.txt", "/../secret.txt", "/%2e%2e/secret.txt", "/%252e%252e/secret.txt", "/exposed.txt", "/.hidden"):
            with self.subTest(path=path):
                self.assertIn(self.request("GET", path)[0], {400, 404})

    def test_model_network_rejects_private_dns_and_allows_ollama_only_loopback(self):
        answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        with patch.object(socket, "getaddrinfo", return_value=answer):
            with self.assertRaises(models.ModelError):
                models._addresses("example.com", 443)
            self.assertEqual(models._addresses("localhost", 11434, True), ["127.0.0.1"])

    def test_model_schema_fallback_and_single_invalid_retry(self):
        settings = config.prepare_config({"api_key": "test-only-placeholder", "model": "demo"})
        schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False}
        response = {"choices": [{"message": {"content": '{"ok":true}'}}]}
        with patch.object(models, "_request", side_effect=[models.FormatUnsupported("格式不支持"), response]) as request:
            self.assertEqual(models.generate_json("测试", schema, settings), {"ok": True})
            self.assertEqual(request.call_args_list[1].args[1]["response_format"], {"type": "json_object"})
        with patch.object(models, "_request", return_value={"choices": [{"message": {"content": '{"wrong":true}'}}]}) as request:
            with self.assertRaises(models.ModelError):
                models.generate_json("测试", schema, settings)
            self.assertEqual(request.call_count, 2)

    def test_model_both_format_downgrades_leave_one_invalid_output_retry(self):
        schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False}
        for provider in ("cloud", "ollama"):
            settings = config.prepare_config({"provider": provider, "api_key": "test-only-placeholder", "model": "demo",
                                              "base_url": "http://127.0.0.1:11434" if provider == "ollama" else "https://example.com/v1"})
            def response(content):
                return {"message": {"content": content}} if provider == "ollama" else {"choices": [{"message": {"content": content}}]}
            with self.subTest(provider=provider), patch.object(models, "_request", side_effect=[
                models.FormatUnsupported("格式不支持"), models.FormatUnsupported("格式不支持"),
                response("不是 JSON"), response('{"ok":true}')]) as request:
                self.assertEqual(models.generate_json("测试", schema, settings), {"ok": True})
                self.assertEqual(request.call_count, 4)
                self.assertNotIn("format", request.call_args_list[2].args[1])
                self.assertNotIn("response_format", request.call_args_list[2].args[1])
            with self.subTest(provider=provider, outcome="invalid"), patch.object(models, "_request", side_effect=[
                models.FormatUnsupported("格式不支持"), models.FormatUnsupported("格式不支持"),
                response("不是 JSON"), response("仍然不是 JSON")]) as request:
                with self.assertRaisesRegex(models.ModelError, "已重试一次"):
                    models.generate_json("测试", schema, settings)
                self.assertEqual(request.call_count, 4)

    def fixture_manifest(self, content: bytes):
        path = "GitHub项目分析/GitHub热点杂志.html"
        manifest = {"revision": "test-revision", "files": [{"path": path, "sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}]}
        return json.dumps(manifest).encode(), path

    def test_sync_hash_validation_and_atomic_preservation(self):
        content = b"<h1>new content</h1>"
        manifest, path = self.fixture_manifest(content)
        with patch.object(sync, "_download", side_effect=[manifest, content]):
            result = sync.sync_content(self.root, "example/project")
        self.assertTrue(result["changed"])
        active = sync.active_site(self.root)
        self.assertEqual((active / path).read_bytes(), content)
        bad_manifest = json.loads(manifest)
        bad_manifest["revision"] = "bad-revision"
        with patch.object(sync, "_download", side_effect=[json.dumps(bad_manifest).encode(), b"wrong"]):
            with self.assertRaises(sync.SyncError):
                sync.sync_content(self.root, "example/project")
        self.assertEqual(sync.active_site(self.root), active)
        lock = sync._SyncLock(self.root / ".runtime/content/.sync.lock").acquire()
        lock.release()

    def test_sync_kernel_lock_survives_stale_file_and_releases_on_process_exit(self):
        path = self.root / "stale.lock"
        path.touch()
        lock = sync._SyncLock(path).acquire()
        try:
            with self.assertRaises(sync.SyncError):
                sync._SyncLock(path).acquire()
        finally:
            lock.release()
        script = ("import os,sys; from pathlib import Path; from gh_daily.sync import _SyncLock; "
                  "lock=_SyncLock(Path(sys.argv[1])).acquire(); os._exit(0)")
        result = subprocess.run([sys.executable, "-c", script, str(path)],
                                cwd=Path(__file__).resolve().parents[1], timeout=10, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertTrue(path.exists())
        lock = sync._SyncLock(path).acquire()
        lock.release()

    def test_local_partial_build_replaces_synced_site_without_second_build(self):
        self.start()
        pointer = self.root / ".runtime/content/active.json"
        pointer.parent.mkdir(parents=True)
        pointer.write_text('{"directory":"previous"}', encoding="utf-8")
        for build_status, expected_pointer in (("success", False), ("skipped", False), ("failed", True)):
            pointer.write_text('{"directory":"previous"}', encoding="utf-8")
            result = {"ok": False, "status": "partial", "tasks": {
                "ai": {"status": "failed"}, "daily": {"status": "success"}, "build": {"status": build_status}}}
            build = Mock()
            modules = {"gh_daily.pipeline": SimpleNamespace(run_update=Mock(return_value=result)),
                       "gh_daily.build": SimpleNamespace(build_site=build)}
            with self.subTest(build_status=build_status), patch.dict(sys.modules, modules):
                self.assertTrue(self.server.run_job("update"))
                acquired = self.server.operation_lock.acquire(timeout=5)
                self.assertTrue(acquired)
                if acquired:
                    self.server.operation_lock.release()
                self.assertEqual(pointer.exists(), expected_pointer)
                self.assertFalse(self.server.job["ok"])
                self.assertEqual(self.server.job["tasks"]["ai"], "failed")
                build.assert_not_called()

    def test_sync_rejects_paths_and_no_repo_is_valid_read_only(self):
        self.assertTrue(sync.sync_content(self.root)["ok"])
        for value in ("../config.json", "dist/.env", "settings/../../secret", "/etc/passwd", "a%2fb", "gh_daily/server.py"):
            self.assertFalse(sync.allowed_content_path(value))
        self.assertTrue(sync.allowed_content_path("GitHub项目分析/历史前身_Markdown/日报.md"))
        self.assertTrue(sync.allowed_content_path("GitHub项目分析/历史前身_Markdown/附件.pdf"))

    def test_service_worker_excludes_private_routes(self):
        script = (Path(__file__).resolve().parents[1] / "web/sw.js").read_text(encoding="utf-8")
        self.assertIn('path.startsWith("/api/")', script)
        self.assertIn('path === "/settings.html"', script)
        self.assertIn('path === "/settings.js"', script)
        self.assertIn('crypto.subtle.digest("SHA-256", bytes)', script)


if __name__ == "__main__":
    unittest.main()
