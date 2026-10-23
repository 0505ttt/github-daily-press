"""报告、档案与杂志的数据回归。"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import build_magazine as magazine
from tools.parse_trending import parse_trending


REPORT = """<html><title>测试榜单</title><body>
<article class="project-card"><a href="https://github.com/sample/project">sample/project</a>
<p class="description">来自仓库说明的项目介绍，用于验证详情解析不会意外抓取其它表格。</p><p>总计 1,200</p></article>
<table><tr><th>排名</th><th>项目</th><th>主语言</th><th>新增</th><th>分类</th></tr>
<tr><td>#1</td><td><a href="https://github.com/sample/project">sample/project</a></td>
<td>Jupyter Notebook</td><td>+100</td><td>AI机器学习 › 工具</td></tr></table>
<table><tr><td>最后一张表不一定是榜单</td></tr></table></body></html>"""

ARCHIVE = """# sample/project

> 项目简介

## 基本信息
- **仓库链接**：https://github.com/sample/project
- **主语言**：Jupyter Notebook
- **Star**：总计 9,999 | 今日新增 +9
- **首次上榜**：2026-10-19
- **最近上榜**：2026-10-20
- **累计上榜**：99 次

## 知识归类
AI机器学习 › Agent框架

## 详细介绍
真实档案正文。

## 历史上榜记录
| 日期 | 当日排名 | Star 总计 | 今日新增 |
|------|----------|-----------|----------|
| 2026-10-19 | #2 | 1,100 | +100 |
| 2026-10-19 | #2 | 1,100 | +100 |
| 2026-10-19 | W#3 | 1,200 | +300 |
| 2026-10-20 | #1 | 1,190 | 暂未获取 |
"""


class MagazineDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_archive_bold_fields_and_weekly_identity(self):
        archive = magazine.parse_archive(self.write("sample-project.md", ARCHIVE))
        self.assertEqual(archive["lang"], "Jupyter Notebook")
        self.assertEqual(archive["first"], "2026-10-19")
        self.assertEqual(archive["last"], "2026-10-20")
        self.assertEqual(archive["cat"], "A-AI机器学习 › Agent框架")
        self.assertEqual(archive["count"], 3)
        self.assertEqual(archive["total"], 1190)  # 最近观察值，不能取历史最大值。
        weekly = next(record for record in archive["records"] if record["type"] == "weekly")
        self.assertEqual(weekly["rank_label"], "W#3")
        self.assertEqual(weekly["id"], "weekly:2026-W43")
        self.assertIsNone(archive["records"][-1]["today"])

    def test_all_category_prefixes_and_legacy_aliases(self):
        for key, name in magazine.CATEGORY_NAMES.items():
            expected = key + "-" + name
            self.assertEqual(magazine.normalize_category(name), expected)
            self.assertEqual(magazine.normalize_category(expected), expected)
        self.assertEqual(magazine.normalize_category("D-后端/服务端 › CRM"), "D-后端-服务端 › CRM")
        self.assertEqual(magazine.normalize_category("AI/机器学习 › Agent"), "A-AI机器学习 › Agent")

    def test_report_periods_and_valid_table(self):
        examples = [("日报_2026-10-19", "daily", "2026-10-19"),
                    ("周报_2026-W43", "weekly", "2026-W43"),
                    ("周报_2026-10-19", "weekly", "2026-W43"),
                    ("月报_2026-10", "monthly", "2026-10")]
        for name, kind, period in examples:
            with self.subTest(name=name):
                report, _ = magazine.parse_report(self.write("GitHub热点" + name + ".html", REPORT))
                self.assertEqual(report["id"], kind + ":" + period)
                self.assertEqual(report["type"], kind)
                self.assertEqual(report["projects"][0]["total"], 1200)
        invalid, note = magazine.parse_report(self.write("GitHub热点周报_2026-W99.html", REPORT))
        self.assertIsNone(invalid)
        self.assertIn("无有效周期", note)

    def test_unknown_card_total_never_borrows_next_project(self):
        report = """<html><body>
<article class="project-card"><a href="https://github.com/sample/first">sample/first</a>
<p>总计暂未获取</p></article>
<article class="project-card"><a href="https://github.com/sample/second">sample/second</a>
<p>总计 98,765</p></article>
<table><tr><td>#1</td><td>sample/first</td><td>Python</td><td>+1</td><td>开发者工具</td></tr>
<tr><td>#2</td><td>sample/second</td><td>Python</td><td>+2</td><td>开发者工具</td></tr></table>
</body></html>"""
        parsed, _ = magazine.parse_report(self.write("GitHub热点日报_2026-10-23.html", report))
        self.assertIsNone(parsed["projects"][0]["total"])
        self.assertEqual(parsed["projects"][1]["total"], 98765)
        self.assertEqual(parsed["meta"]["miss_total"], 1)

    def test_no_card_fallback_stops_at_next_repository(self):
        body = "sample/first 总计暂未获取 sample/second 总计 98,765"
        self.assertIsNone(magazine.extract_total_from_window(body, "sample/first"))
        self.assertEqual(magazine.extract_total_from_window(body, "sample/second"), 98765)
        spaced = "sample/first 总计暂未获取 sample / second 总计 98,765"
        self.assertIsNone(magazine.extract_total_from_window(spaced, "sample/first"))
        self.assertIsNone(magazine.extract_total_from_window("sample/first-more 总计 98,765", "sample/first"))

    def test_ai_multiline_all_sources_and_collection_footer(self):
        path = self.write("2026-10-23-AI日报.md", """# AI前沿日报
## 一、大模型动态
- **模型更新** — 第一行介绍。
  第二行补充。[官方](https://example.org/news)｜[论文](https://example.org/paper)（附说明）
- **工程更新**：继续保留中文冒号后的介绍。[来源](https://example.org/engineering)

**今日一句话总结**：这是总结，不是新闻。
**今日采集情况**：这是采集日志，不是新闻。
""")
        day = magazine.parse_ai_md(path)
        items = day["sections"][0]["items"]
        self.assertEqual(len(items), 2)
        self.assertIn("第二行补充", items[0]["d"])
        self.assertEqual(len(items[0]["sources"]), 2)
        self.assertNotIn("](https", items[0]["d"])
        self.assertEqual(items[1]["d"], "继续保留中文冒号后的介绍。")

    def test_build_period_counts_merge_and_daily_numbering(self):
        analysis = self.root / "GitHub项目分析"
        for name in ("日报_2026-10-19", "日报_2026-10-20", "周报_2026-W43", "月报_2026-10"):
            self.write("GitHub项目分析/GitHub热点" + name + ".html", REPORT)
        self.write("GitHub项目分析/GitHub热点周报_2026-W44.html", "<html></html>")
        self.write("GitHub项目分析/史料.pdf", "测试占位文件")
        self.write("GitHub项目分析/项目分类库/sample-project.md", ARCHIVE)
        with patch.multiple(magazine, ANALYSIS=analysis, LIB=analysis / "项目分类库", AI_DIR=self.root / "AI前沿资讯/日报"):
            db, _, skipped = magazine.build_db()
        self.assertEqual(db["meta"]["count_daily"], 2)
        self.assertEqual(db["meta"]["count_weekly"], 1)
        self.assertEqual(db["meta"]["count_monthly"], 1)
        self.assertEqual(db["meta"]["pdf_files"], ["史料.pdf"])
        self.assertEqual(len(skipped), 1)
        self.assertEqual([day["issue"] for day in db["issues"] if day["type"] == "daily"], [1, 2])
        self.assertEqual(db["projects"]["sample/project"]["count"], 3)
        self.assertEqual(db["projects"]["sample/project"]["total"], 1190)
        self.assertFalse(any(record["type"] == "monthly" for record in db["projects"]["sample/project"]["records"]))

    def test_json_embedding_does_not_close_script(self):
        db = {"generated_at": "2026-10-23", "meta": {"count_days": 0, "count_repos": 0, "count_projects": 0},
              "payload": "</script><script>alert(1)</script>"}
        html = magazine.render_html(db)
        soup = magazine.BeautifulSoup(html, "html.parser")
        self.assertEqual(json.loads(soup.find(id="DB").string)["payload"], db["payload"])
        self.assertNotIn("<script>alert(1)</script>", html)

    @unittest.skipUnless(shutil.which("node"), "需要 Node.js 执行内嵌脚本逻辑检查")
    def test_sidebar_closed_is_inert_and_returns_focus_on_resize(self):
        script = magazine.SHELL.split("function sideOff(){", 1)[1].split("\ntog.addEventListener", 1)[0]
        script = "function sideOff(){" + script
        harness = r"""
const assert=require('node:assert/strict');
const classes=new Set();
let storedOff=false;
const search={};
const side={
  attributes:{},
  contains:function(node){return node===search;},
  setAttribute:function(name,value){this.attributes[name]=value;},
  set inert(value){
    if(value)assert.notEqual(document.activeElement,search,'必须在设置 inert 之前交还焦点');
    this._inert=value;
  },
  get inert(){return this._inert;}
};
const tog={attributes:{},setAttribute:function(name,value){this.attributes[name]=value;},
  focus:function(){document.activeElement=this;}};
const document={activeElement:search,getElementById:function(){return side;},body:{classList:{
  contains:function(name){return classes.has(name);},
  remove:function(name){classes.delete(name);},
  toggle:function(name,enabled){if(enabled)classes.add(name);else classes.delete(name);}
}}};
const window={innerWidth:390};
const localStorage={getItem:function(){return storedOff?'1':'0';}};
""" + script + r"""
applySide();
assert.equal(side.inert,true);
assert.equal(side.attributes['aria-hidden'],'true');
assert.equal(tog.attributes['aria-expanded'],'false');
assert.equal(document.activeElement,tog);
classes.add('side-on');
document.activeElement=search;
applySide();
assert.equal(side.inert,false);
assert.equal(document.activeElement,search);
assert.equal(tog.attributes['aria-expanded'],'true');
window.innerWidth=1280;
storedOff=true;
applySide();
assert.equal(side.inert,true);
assert.equal(document.activeElement,tog);
storedOff=false;
applySide();
assert.equal(side.inert,false);
document.activeElement=search;
classes.delete('side-on');
window.innerWidth=390;
applySide();
assert.equal(side.inert,true);
assert.equal(document.activeElement,tog);
"""
        result = subprocess.run([shutil.which("node"), "-"], input=harness, text=True, encoding="utf-8",
                                capture_output=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


class TrendingTests(unittest.TestCase):
    def test_missing_rows_keep_real_rank_and_extra_classes(self):
        html = """<article class="Box-row"><h2>不可识别的行</h2></article>
<article class="Box-row"><h2><a href="/sample/project">仓库</a></h2><p>实际描述</p>
<span class="d-inline-block color-fg-muted float-sm-right">123 stars today</span>
<a href="/sample/project/stargazers">1,200</a></article>"""
        projects = parse_trending(html)
        self.assertEqual(projects[0]["rank"], 2)
        self.assertEqual(projects[0]["today_stars"], "123 stars today")
        self.assertEqual(projects[0]["total_stars"], "1,200")


if __name__ == "__main__":
    unittest.main()
