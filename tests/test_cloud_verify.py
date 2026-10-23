"""云端验收回归；网络在测试中受控，不产生真实模型调用。"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from gh_daily import cloud_verify as verify
from gh_daily import models, pipeline, sources
from tests.test_pipeline import ai_collection, fake_model, snapshot


class CloudValidationTests(unittest.TestCase):
    def test_workflow_only_reads_model_configuration_from_secrets(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/daily.yml").read_text(encoding="utf-8")
        for name in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
            self.assertNotIn("vars." + name, workflow)
            self.assertEqual(workflow.count("secrets." + name), 2)

    def first(self):
        return {"tasks": {name: {"status": "success", "count": 1} for name in verify.REQUIRED}}

    def test_first_rejects_skipped_failed_and_empty_editorial(self):
        day = date(2026, 10, 23)
        calls = {"model_requests": 2, "source_requests": 1}
        verify._validate_first(self.first(), calls, day)
        for name in verify.REQUIRED:
            for status in ("skipped", "failed", "not_due"):
                state = self.first()
                state["tasks"][name]["status"] = status
                with self.subTest(name=name, status=status), self.assertRaises(verify.VerificationError):
                    verify._validate_first(state, calls, day)
        state = self.first()
        state["tasks"]["ai"]["count"] = 0
        with self.assertRaises(verify.VerificationError):
            verify._validate_first(state, calls, day)
        for calls in ({"model_requests": 0, "source_requests": 1}, {"model_requests": 2, "source_requests": 0}):
            with self.assertRaises(verify.VerificationError):
                verify._validate_first(self.first(), calls, day)

    def test_counting_forwards_real_functions_without_storing_payload(self):
        marker = {"opaque": "request-body-must-not-be-retained"}
        with patch.object(models, "_request", return_value={"ok": True}) as model, patch.object(sources, "_download_once", return_value="source") as source:
            with verify._count_calls() as calls:
                self.assertEqual(models._request({}, marker), {"ok": True})
                self.assertEqual(sources._download_once("https://example.test"), "source")
            self.assertEqual(calls, {"model_requests": 1, "source_requests": 1})
            model.assert_called_once_with({}, marker)
            source.assert_called_once_with("https://example.test")
            self.assertIs(models._request, model)

    def test_repeat_rejects_requests_and_changed_archive_hashes(self):
        state = {"tasks": {name: {"status": "skipped"} for name in ("ai", "daily", "build")}}
        state["tasks"]["daily_archives"] = {"status": "success", "added": 0, "updated": 0, "changed": False}
        zero = {"model_requests": 0, "source_requests": 0}
        day = date(2026, 10, 23)
        verify._validate_repeat({"a": "same"}, {"a": "same"}, state, zero, day)
        for calls, after in (({"model_requests": 1, "source_requests": 0}, {"a": "same"}), (zero, {"a": "changed"})):
            with self.assertRaises(verify.VerificationError):
                verify._validate_repeat({"a": "same"}, after, state, calls, day)
        state["tasks"]["daily_archives"]["added"] = 1
        with self.assertRaises(verify.VerificationError):
            verify._validate_repeat({}, {}, state, zero, day)

    def test_midnight_refuses_relabeling_live_data(self):
        with patch.object(pipeline, "_today", return_value=date(2026, 10, 24)):
            with self.assertRaises(verify.VerificationError):
                verify._same_day(date(2026, 10, 23))

    def test_missing_model_settings_exports_only_safe_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with patch.dict(os.environ, {"GH_DAILY_API_KEY": "", "GH_DAILY_BASE_URL": "https://private-endpoint.test", "GH_DAILY_MODEL": "private-model"}), patch.object(pipeline, "run_update") as update:
                with self.assertRaises(verify.VerificationError):
                    verify.generate(Path(__file__).resolve().parents[1], root / "result")
            update.assert_not_called()
            contents = (root / "result/verification.json").read_text(encoding="utf-8")
            self.assertNotIn("private-endpoint", contents)
            self.assertNotIn("private-model", contents)
            self.assertEqual([item.name for item in (root / "result").iterdir()], ["verification.json"])

    def test_end_to_end_uses_blank_workspace_and_repeat_skips_model(self):
        def collect(**kwargs):
            sources._download_once("https://example.test")
            return copy.deepcopy(ai_collection())

        def model(settings, payload):
            schema = payload["response_format"]["json_schema"]["schema"]
            return {"choices": [{"message": {"content": json.dumps(fake_model("", schema), ensure_ascii=False)}}]}

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory).resolve() / "export"
            with patch.dict(os.environ, {"GH_DAILY_PROVIDER": "cloud", "GH_DAILY_BASE_URL": "https://private-endpoint.test/v1", "GH_DAILY_API_KEY": "unit-test-private-key", "GH_DAILY_MODEL": "test-model"}), patch.object(pipeline, "_today", return_value=date(2026, 10, 23)), patch.object(sources, "collect_ai", side_effect=collect), patch.object(sources, "collect_trending", side_effect=lambda period, **_: snapshot(period)), patch.object(sources, "enrich_projects", return_value=[]), patch.object(sources, "_download_once", return_value="data"), patch.object(models, "_request", side_effect=model) as requests:
                result = verify.generate(Path(__file__).resolve().parents[1], output)
            self.assertTrue(result["generation_ok"])
            self.assertFalse(result["ok"])
            self.assertEqual(requests.call_count, 2)
            self.assertEqual(result["repeat_calls"], {"model_requests": 0, "source_requests": 0})
            self.assertEqual(result["first_issue"], 1)
            self.assertFalse((output / ".runtime").exists())
            self.assertFalse((output / "dist/settings.html").exists())
            self.assertFalse((output / "dist/settings.js").exists())
            self.assertEqual(len(list((output / "GitHub项目分析").glob("GitHub热点日报_*.html"))), 1)
            for path in output.rglob("*"):
                if path.is_file():
                    self.assertNotIn(b"unit-test-private-key", path.read_bytes())

    def test_file_selection_blocks_hidden_files_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "dist").mkdir()
            hidden = root / "dist/.private.json"
            hidden.write_text("{}")
            with self.assertRaises(verify.VerificationError):
                verify._content_files(root)
            hidden.unlink()
            target = root / "dist/link.html"
            target.symlink_to(root / "outside")
            with self.assertRaises(verify.VerificationError):
                verify._content_files(root)

    def test_branch_identity_is_not_user_supplied(self):
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "example/press", "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2"}):
            self.assertEqual(verify._identity()[1], "refs/heads/cloud-validation/123-2")
            for key, value in (("GITHUB_RUN_ID", "123;command"), ("GITHUB_REPOSITORY", "../press"), ("GITHUB_RUN_ATTEMPT", "../main")):
                with patch.dict(os.environ, {key: value}), self.assertRaises(verify.VerificationError):
                    verify._identity()

    def test_writeback_rejects_path_traversal_before_network(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"GITHUB_REPOSITORY": "example/press", "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1"}):
            root = Path(directory)
            verify._write(root / verify.SUMMARY, {"generation_ok": True, "files": {"../outside.md": "a" * 64}})
            with patch.object(verify, "_git") as git, self.assertRaises(verify.VerificationError):
                verify.writeback(root, root / "state.json")
            git.assert_not_called()

    def test_cleanup_only_deletes_own_unchanged_commit_with_lease(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"GITHUB_REPOSITORY": "example/press", "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1"}):
            state = Path(directory) / "state.json"
            ref, commit = "refs/heads/cloud-validation/123-1", "a" * 40
            verify._write(state, {"ref": ref, "commit": commit})
            with patch.object(verify, "_git", return_value="b" * 40 + "\t" + ref) as git, self.assertRaises(verify.VerificationError):
                verify.cleanup(state)
            self.assertEqual(git.call_count, 1)
            self.assertTrue(state.exists())
            with patch.object(verify, "_git", side_effect=[commit + "\t" + ref, "", "", ""]) as git:
                verify.cleanup(state)
            self.assertIn("--force-with-lease=" + ref + ":" + commit, git.call_args_list[2].args)
            self.assertFalse(state.exists())

    def test_real_git_writeback_fetch_readback_and_delete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            remote = root / "remote.git"
            subprocess.run(["git", "init", "--quiet", "--bare", str(remote)], check=True, capture_output=True)
            output = root / "output"
            (output / "dist").mkdir(parents=True)
            page = output / "dist/index.html"
            page.write_text("<!doctype html><p>经过检查的公开日报</p>", encoding="utf-8")
            verify._write(output / verify.SUMMARY, {"ok": False, "generation_ok": True, "writeback": "pending",
                                                 "files": {"dist/index.html": hashlib.sha256(page.read_bytes()).hexdigest()}})
            state = root / "state.json"
            ref = "refs/heads/cloud-validation/123-1"
            with patch.object(verify, "_identity", return_value=(str(remote), ref)), patch.object(verify, "_git", wraps=verify._git) as git:
                result = verify.writeback(output, state)
            self.assertTrue(result["ok"])
            self.assertEqual(result["writeback"], "verified_and_branch_deleted")
            self.assertFalse(state.exists())
            self.assertTrue(any("fetch" in call.args for call in git.call_args_list))
            self.assertEqual(subprocess.run(["git", "--git-dir", str(remote), "for-each-ref"], check=True, capture_output=True, text=True).stdout, "")

    def test_readback_failure_still_deletes_own_verification_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            remote = root / "remote.git"
            subprocess.run(["git", "init", "--quiet", "--bare", str(remote)], check=True, capture_output=True)
            output = root / "output"
            (output / "dist").mkdir(parents=True)
            page = output / "dist/index.html"
            page.write_text("公开日报", encoding="utf-8")
            verify._write(output / verify.SUMMARY, {"generation_ok": True,
                                                 "files": {"dist/index.html": hashlib.sha256(page.read_bytes()).hexdigest()}})
            real_git = verify._git

            def fail_fetch(root, *arguments):
                if "fetch" in arguments:
                    raise verify.VerificationError("模拟远端读回失败")
                return real_git(root, *arguments)

            with patch.object(verify, "_identity", return_value=(str(remote), "refs/heads/cloud-validation/123-1")), patch.object(verify, "_git", side_effect=fail_fetch), self.assertRaises(verify.VerificationError):
                verify.writeback(output, root / "state.json")
            self.assertEqual(subprocess.run(["git", "--git-dir", str(remote), "for-each-ref"], check=True, capture_output=True, text=True).stdout, "")


if __name__ == "__main__":
    unittest.main()
