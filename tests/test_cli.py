"""命令行在非 UTF-8 管道中的中文输出回归。"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliEncodingTests(unittest.TestCase):
    def run_cli(self, command):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "empty"
            root.mkdir()
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith("GH_DAILY_")}
            environment.update({"GH_DAILY_CONFIG_DIR": str(base / "config"),
                                "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"})
            return subprocess.run(
                [sys.executable, "-m", "gh_daily", "--root", str(root), command],
                cwd=Path(__file__).resolve().parents[1], env=environment,
                capture_output=True, timeout=30, check=False)

    def test_doctor_json_uses_utf8_when_pipe_defaults_to_cp1252(self):
        result = self.run_cli("doctor")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, b"")
        report = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["静态站点"])
        self.assertIn("模型设置", report)
        self.assertEqual(report["隐私问题数"], 0)

    def test_build_error_uses_utf8_when_pipe_defaults_to_cp1252(self):
        result = self.run_cli("build")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b"")
        self.assertIn("操作未完成：", result.stderr.decode("utf-8"))
        self.assertNotIn(b"UnicodeEncodeError", result.stderr)


if __name__ == "__main__":
    unittest.main()
