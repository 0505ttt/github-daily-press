"""本地空白首刊和持久编号不受公共仓库历史影响。"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gh_daily.build import build_site
from gh_daily.local import prepare_local_workspace
from tests.test_magazine import REPORT


class LocalWorkspaceTests(unittest.TestCase):
    def test_empty_start_first_own_issue_and_restart_preserves_number(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'GH_DAILY_DATA_DIR': directory}):
            root = prepare_local_workspace(source)
            data = json.loads((root / 'tools/_杂志数据.json').read_text(encoding='utf-8'))
            self.assertEqual(data['issues'], [])
            self.assertEqual(data['projects'], {})
            self.assertEqual(data['ai_days'], {})
            self.assertFalse(list((root / 'GitHub项目分析').glob('GitHub热点日报_*.html')))
            first = root / 'GitHub项目分析/GitHub热点日报_2026-10-23.html'
            first.write_text(REPORT, encoding='utf-8')
            build_site(root)
            restarted = prepare_local_workspace(source)
            data = json.loads((restarted / 'tools/_杂志数据.json').read_text(encoding='utf-8'))
            self.assertEqual(len(data['issues']), 1)
            self.assertEqual(data['issues'][0]['issue'], 1)
            self.assertEqual(data['issues'][0]['date'], '2026-10-23')
            self.assertEqual(first.read_text(encoding='utf-8'), REPORT)


if __name__ == '__main__':
    unittest.main()
