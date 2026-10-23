#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 热点杂志 · 构建脚本（融合版）
扫描 GitHub项目分析/ 下全部日报/周报/月报 HTML + AI前沿资讯/日报/*.md + 项目分类库档案 md
→ 生成单文件自包含杂志总览页（Businessweek 大字报风）。

用法：
    tools/.venv/bin/python tools/build_magazine.py

数据源与锚点（经全量实测）：
- 期数据主锚点 = 每份报告的速览表（5 列恒定：排名/项目/主语言/今日⭐/知识归类）
- 卡片辅锚点 = .project-card 容器（补档版/融合版）→ 早期原始版 fallback 为「github 链接向上爬」
- AI 速递 = 日报 .ai-band 板块（10-19 起）+ AI前沿资讯/日报/*.md 全量（md 为权威全量源）
- 项目档案 = 项目分类库/**/owner-repo.md 的「历史上榜记录」表（时间线权威源，双源合并）
- 幂等全量重建：重跑即自动纳入新落盘的报告；同期同 repo 去重
输出：
- GitHub项目分析/GitHub热点杂志.html（内嵌数据，file:// 离线可开）
- tools/_杂志数据.json（数据真源，构建产物）
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / "GitHub项目分析"
AI_DIR = ROOT / "AI前沿资讯" / "日报"
LIB = ANALYSIS / "项目分类库"
OUT_HTML = ANALYSIS / "GitHub热点杂志.html"
OUT_JSON = ROOT / "tools" / "_杂志数据.json"

WEEKDAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
HOT_LINE = 800  # 今日 +800 星以上标 HOT

REPO_HREF = re.compile(r"https?://github\.com/([\w.\-]+/[\w.\-]+)/?$")
RE_NOT_DIGIT = re.compile(r"[^\d]")
RE_REPO_NAME = re.compile(r"^[\w.\-]+/[\w.\-]+$")
P_TOTAL = [
    re.compile(r"总计\D{0,10}([\d][\d,]{2,})"),
    re.compile(r"总\s*Star\s*[：:]?\s*([\d][\d,]{2,})", re.I),
    re.compile(r"([\d][\d,]{2,})\s*总计"),
    re.compile(r"([\d][\d,]{2,})\s*[⭐★]"),
    re.compile(r"[⭐★]\s*([\d][\d,]{2,})"),
    re.compile(r"Stars?\s*[：:]\s*([\d,]{3,})", re.I),
    re.compile(r"([\d,]{3,})\s*stars?", re.I),
]
RE_SNAP = re.compile(r"(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2})\s*UTC")
RE_SNAP_URL = re.compile(r"https://web\.archive\.org/web/\d+/")
CATEGORY_NAMES = {
    "A": "AI机器学习", "B": "开发者工具", "C": "前端-Web", "D": "后端-服务端",
    "E": "基础设施-DevOps", "F": "数据-数据库", "G": "安全", "H": "移动开发",
    "I": "系统-底层", "J": "区块链-Web3", "K": "游戏-图形", "L": "学习资源-其他",
}


def normalize_category(value):
    """兼容早期中文分类与带字母的分类，统一一级分类名。"""
    parts = re.split(r"\s*[›>]\s*", value.strip().strip("*"))
    if not parts or not parts[0]:
        return ""
    first = parts[0]
    prefix = re.match(r"^([A-L])\s*[-－]", first)
    if prefix:
        key = prefix.group(1)
    else:
        compact = re.sub(r"[\s/／-]", "", first).lower()
        aliases = {re.sub(r"[\s/-]", "", name).lower(): key for key, name in CATEGORY_NAMES.items()}
        aliases.update({"ai/机器学习".replace("/", ""): "A", "ai": "A", "前端web": "C",
                        "devops": "E", "学习资源": "L", "其他": "L", "区块链": "J"})
        key = aliases.get(compact)
    if key:
        parts[0] = key + "-" + CATEGORY_NAMES[key]
    return " › ".join(parts)


def report_period(path):
    """返回周期类型、周期键和展示日期，兼容旧日期式周报文件名。"""
    name = path.stem
    if "周报" in name:
        match = re.search(r"(\d{4})-W(\d{1,2})(?!\d)", name, re.I)
        if match:
            day = date.fromisocalendar(int(match[1]), int(match[2]), 1)
        else:
            match = re.search(r"\d{4}-\d{2}-\d{2}", name)
            if not match:
                raise ValueError("文件名无有效周号")
            day = date.fromisoformat(match[0])
        return "weekly", iso_week(day), day
    if "月报" in name:
        match = re.search(r"(\d{4}-\d{2})(?!\d)", name)
        if not match:
            raise ValueError("文件名无有效月份")
        day = date.fromisoformat(match[1] + "-01")
        return "monthly", match[1], day
    match = re.search(r"\d{4}-\d{2}-\d{2}", name)
    if not match:
        raise ValueError("文件名无有效日期")
    day = date.fromisoformat(match[0])
    return "daily", day.isoformat(), day


def iso_week(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def parse_int(s):
    digits = RE_NOT_DIGIT.sub("", s or "")
    return int(digits) if digits else None


# ---------------------------------------------------------------------------
# 一、日报/周报/月报 HTML 解析
# ---------------------------------------------------------------------------

def find_card_by_climb(link_el):
    """早期原始版：从仓库链接向上爬，取祖先链上文本量最大的卡片容器
    （不在 card-head 等短子块提前停——star/描述可能在外层）。"""
    node, best = link_el, None
    for _ in range(10):
        node = node.parent
        if node is None or node.name in ("body", "html", "[document]"):
            break
        cls = " ".join(node.get("class", [])) if isinstance(node.get("class"), list) else ""
        if "card" in cls or node.name == "article":
            tlen = len(node.get_text(" ", strip=True))
            if best is None or tlen > len(best.get_text(" ", strip=True)):
                best = node
    return best


def collect_cards(soup):
    """repo → 卡片容器。优先 .project-card（补档/融合版），fallback 爬链（早期原始版）。
    严格限定在卡片容器内取链接，避开速览表与 ai-band 的 github 链接。"""
    cards = {}
    for card in soup.select(".project-card"):
        a = card.find("a", href=True)
        if a is None:
            continue
        m = REPO_HREF.match(a["href"].rstrip("/"))
        if m and m.group(1) not in cards:
            cards[m.group(1)] = card
    for a in soup.find_all("a", href=True):
        m = REPO_HREF.match(a["href"].rstrip("/"))
        if not m or m.group(1) in cards:
            continue
        card = find_card_by_climb(a)
        if card is not None:
            cards[m.group(1)] = card
    return cards


def extract_total_stars(text):
    cleaned = re.sub(r"\+\s?[\d][\d,]*", " ", text)  # 剔除今日新增形态防误配
    for pat in P_TOTAL:
        m = pat.search(cleaned)
        if m:
            return parse_int(m.group(1))
    return None


def extract_fields(card):
    tagline = ""
    el = card.find(class_=re.compile(r"tag.?line|tagline|one.?liner"))
    if el is not None:
        tagline = el.get_text(" ", strip=True)
    desc = ""
    el = card.find(class_=re.compile(r"^desc$|description|detail|introduce"))
    if el is not None and len(el.get_text(strip=True)) > 20:
        desc = el.get_text(" ", strip=True)
    if not desc:
        best = ""
        for blk in card.find_all(["p", "div", "span"]):
            t = blk.get_text(" ", strip=True)
            if len(t) > len(best) and len(t) > 30 and "适用领域" not in t and "知识归类" not in t:
                best = t
        desc = best
    if desc.startswith("【补档】"):
        desc = desc.replace("【补档】本报告由 Wayback Machine 快照自动重建，详细介绍从略；快照期仓库描述：", "")
        desc = desc.replace("快照期仓库描述：", "").strip()
        if desc == "无":
            desc = ""
    field = ""
    el = card.find(string=re.compile("适用领域"))
    if el is not None and el.parent is not None:
        field = el.parent.get_text(" ", strip=True).replace("适用领域", "").strip("：: |｜")
    return tagline, desc, field


def extract_wind(soup):
    for h in soup.find_all(["h2", "h3"]):
        t = h.get_text(strip=True)
        if re.search(r"风向|概览|速读|速览", t) and len(t) < 30:
            container = h.parent if h.parent and h.parent.name not in ("body", "html") else h
            txt = container.get_text(" ", strip=True)
            txt = re.sub(r"^" + re.escape(t) + r"\s*", "", txt).strip()
            if 20 < len(txt) < 1500:
                return txt
            nxt = h.find_next_sibling()
            if nxt is not None:
                t2 = nxt.get_text(" ", strip=True)
                if len(t2) > 20:
                    return t2
    return ""


def extract_ai_band(soup):
    """融合版日报 .ai-band 速递（10-19 起存在）→ 条目列表。"""
    band = soup.select_one(".ai-band")
    if band is None:
        return []
    items = []
    for li in band.find_all("li"):
        a = li.find("a", href=True)
        strong = li.find("strong")
        if strong is None:
            continue
        title = strong.get_text(" ", strip=True)
        full = li.get_text(" ", strip=True)
        desc = full.replace(title, "", 1).strip(" —-：:，, ")
        if a is not None:
            desc = re.sub(r"\[[^\]]*\]$", "", desc).strip()
        items.append({
            "t": title,
            "d": desc,
            "url": a["href"] if a else "",
            "src": a.get_text(strip=True).strip("[]") if a else "",
        })
    return items


def extract_total_from_window(body_text, repo):
    """无卡片时的保守兜底：窗口止于下一仓库名，禁止借用邻项总星。"""
    exact_repo = re.compile(r"(?<![\w.\-/])" + re.escape(repo) + r"(?![\w.\-/])")
    next_repo = re.compile(r"[\w.\-]+\s*/\s*[\w.\-]+")
    for match in exact_repo.finditer(body_text):
        window = body_text[match.end():match.end() + 320]
        boundary = next_repo.search(window)
        if boundary:
            window = window[:boundary.start()]
        t = extract_total_stars(window)
        if t is not None:
            return t
    return None


def parse_report(path: Path):
    try:
        kind, period, d = report_period(path)
    except ValueError:
        return None, f"跳过（文件名无有效周期）：{path.name}"

    text = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(text, "html.parser")
    title = soup.title.get_text() if soup.title else ""
    backfill = bool(soup.select_one(".badge-backfill")) or "补档" in title

    snapshot, snapshot_url = "", ""
    if backfill:
        fm = RE_SNAP.search(text)
        if fm:
            snapshot = fm.group(1) + " UTC"
        um = RE_SNAP_URL.search(text)
        if um:
            snapshot_url = um.group(0)

    tables = soup.find_all("table")
    if not tables:
        return None, f"跳过（无速览表）：{path.name}"
    # 月报可能有多张统计表，以真实包含仓库名的五列表格为锚点。
    quick = max(tables, key=lambda table: sum(
        1 for row in table.find_all("tr")
        if len(row.find_all("td")) >= 5
        and RE_REPO_NAME.fullmatch(row.find_all("td")[1].get_text(" ", strip=True))
    ))

    cards = collect_cards(soup)
    body_text = soup.get_text(" ", strip=True)
    projects, seen = [], set()
    miss_total, miss_desc = 0, 0
    for tr in quick.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue
        rank = parse_int(tds[0].get_text(strip=True))
        repo = tds[1].get_text(" ", strip=True).strip()
        if not RE_REPO_NAME.match(repo) or repo in seen:  # 同期同 repo 去重
            continue
        seen.add(repo)
        a = tds[1].find("a", href=True)
        url = a["href"] if a else f"https://github.com/{repo}"
        lang = tds[2].get_text(" ", strip=True)
        today = parse_int(tds[3].get_text(strip=True))
        cat = normalize_category(tds[4].get_text(" ", strip=True))

        total, tagline, desc, field = None, "", "", ""
        card = cards.get(repo)
        if card is not None:
            ctext = card.get_text(" ", strip=True)
            total = extract_total_stars(ctext)
            tagline, desc, field = extract_fields(card)
        else:
            # 已匹配卡片中的缺失值必须保持缺失，不能到全文寻找邻项数字。
            total = extract_total_from_window(body_text, repo)
        if total is None:
            miss_total += 1
        if not desc:
            miss_desc += 1

        projects.append({
            "rank": rank, "repo": repo, "url": url, "lang": lang,
            "today": today, "total": total, "cat": cat,
            "tagline": tagline, "desc": desc, "field": field,
            "hot": bool(today and today >= HOT_LINE),
        })

    if not projects:
        return None, f"跳过（速览表无有效行）：{path.name}"

    ai_items = extract_ai_band(soup)
    day = {
        "id": f"{kind}:{period}",
        "period": period,
        "file": path.name,
        "date": d.isoformat(),
        "issue": 0,
        "type": kind,
        "weekday": WEEKDAY_CN[d.weekday()],
        "week": iso_week(d),
        "month": d.strftime("%Y-%m"),
        "backfill": backfill,
        "snapshot": snapshot,
        "snapshot_url": snapshot_url,
        "wind": extract_wind(soup),
        "ai": ai_items,
        "projects": projects,
        "meta": {
            "quick_rows": len(projects),
            "cards": len(cards),
            "ai_items": len(ai_items),
            "miss_total": miss_total,
            "miss_desc": miss_desc,
        },
    }
    note = (f"{period}{'（周报）' if kind == 'weekly' else '（月报）' if kind == 'monthly' else ''}：{len(projects)} 项目"
            f"{'，补档快照 ' + snapshot if backfill else ''}"
            f"；总星缺失 {miss_total}，描述缺失 {miss_desc}，AI速递 {len(ai_items)} 条")
    return day, note


# ---------------------------------------------------------------------------
# 二、AI 前沿日报 md 解析（全量权威源）
# ---------------------------------------------------------------------------
RE_MD_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def parse_ai_md(path: Path):
    """AI 日报 md → {date, sections:[{title, items:[{t,d,url,src}]}]}"""
    m = RE_MD_DATE.search(path.stem)
    if not m:
        return None
    sections, cur_title, cur_items = [], "", []
    pending = []

    def flush_item():
        if not pending or not cur_title:
            pending.clear()
            return
        block = " ".join(pending)
        pending.clear()
        match = re.match(r"(?:[-*]\s*)?\*\*(.+?)\*\*(.*)", block)
        if not match or re.search(r"采集情况|一句话总结|今日总结", match[1]):
            return
        links = []
        for source in re.finditer(r"\[([^\]]*)\]\((https?://[^\s)]+)\)", match[2]):
            item = {"src": source[1].strip(), "url": source[2]}
            if item not in links:
                links.append(item)
        desc = re.sub(r"\[[^\]]*\]\(https?://[^\s)]+\)", "", match[2])
        desc = re.sub(r"^\s*(?:[（(][⭐★]?\s*[\d,]+\s*[）)])?\s*[—–:：-]?\s*", "", desc)
        desc = desc.replace("**", "").strip(" ｜|，, ")
        cur_items.append({"t": match[1].strip(), "d": desc,
                          "url": links[0]["url"] if links else "",
                          "src": links[0]["src"] if links else "", "sources": links})

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## ") or re.match(r"^[-*_]{3,}$", line):
            flush_item()
            if cur_title and cur_items:
                sections.append({"title": cur_title, "items": cur_items})
            title = line[3:].strip() if line.startswith("## ") else ""
            cur_title = "" if re.search(r"采集情况|一句话总结|今日总结", title) else title
            cur_items = []
        elif re.match(r"^(?:[-*]\s*)?\*\*", line):
            flush_item()
            if re.match(r"^(?:[-*]\s*)?\*\*(?:今日)?(?:采集情况|一句话总结|总结)", line):
                if cur_title and cur_items:
                    sections.append({"title": cur_title, "items": cur_items})
                cur_title, cur_items = "", []
            elif cur_title:
                pending.append(line)
        elif pending and line:
            pending.append(line)
    flush_item()
    if cur_title and cur_items:
        sections.append({"title": cur_title, "items": cur_items})
    if not sections:
        return None
    return {"date": m.group(1), "file": path.name, "sections": sections}


def collect_ai_days():
    out = {}
    if not AI_DIR.exists():
        return out
    for f in sorted(AI_DIR.glob("*-AI日报.md")):
        r = parse_ai_md(f)
        if r:
            out[r["date"]] = r
    return out


# ---------------------------------------------------------------------------
# 三、项目分类库档案解析（时间线权威源）
# ---------------------------------------------------------------------------

def parse_archive(path: Path):
    """档案 md → project dict（记录表 + 基本信息）。"""
    text = path.read_text(encoding="utf-8")
    repo = ""
    for ln in text.splitlines()[:3]:
        m = re.match(r"#\s+([\w.\-]+/[\w.\-]+)", ln.strip())
        if m:
            repo = m.group(1)
            break
    if not repo:
        return None
    tagline = ""
    m = re.search(r"^>\s*(.+)$", text, re.M)
    if m:
        tagline = m.group(1).strip()

    # 标签加粗不属于字段内容；先移除标记，防止“**主语言**：”漏匹配。
    plain = text.replace("**", "")

    def grab(pattern, default=""):
        m = re.search(pattern, plain, re.M)
        return m.group(1).strip() if m else default

    lang = grab(r"主语言[：:][ \t]*([^\n|]+)")
    total = parse_int(grab(r"总计\s*([\d,]+)"))
    first = grab(r"首次上榜[：:]\s*(\d{4}-\d{2}-\d{2})")
    last = grab(r"最近上榜[：:]\s*(\d{4}-\d{2}-\d{2})")
    count = parse_int(grab(r"累计上榜[：:]?\s*(\d+)\s*次"))
    url = grab(r"仓库链接[：:][ \t]*(https://github\.com/[\w.\-]+/[\w.\-]+)")

    cat = ""
    m = re.search(r"##[ \t]*知识归类[ \t]*\n+[ \t]*([^\n]+)", plain)
    if m:
        cat = normalize_category(m.group(1).strip())

    desc = ""
    m = re.search(r"##\s*详细介绍\s*\n+\s*(.+?)(?=\n\s*##|\Z)", text, re.S)
    if m:
        desc = m.group(1).strip().strip("- ")

    records = []
    in_table = False
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("|") and re.search(r"日期.*排名", s):
            in_table = True
            continue
        if in_table:
            if not s.startswith("|"):
                if records:
                    break
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) >= 4:
                dm = RE_MD_DATE.search(cells[0])
                if dm:
                    weekly = bool(re.match(r"W\s*#?\s*\d+", cells[1], re.I))
                    kind = "weekly" if weekly else "daily"
                    period = iso_week(date.fromisoformat(dm.group(1))) if weekly else dm.group(1)
                    records.append({
                        "date": dm.group(1),
                        "rank": parse_int(cells[1]),
                        "rank_label": "W#" + str(parse_int(cells[1])) if weekly else "#" + str(parse_int(cells[1])),
                        "type": kind, "period": period, "id": f"{kind}:{period}",
                        "total": parse_int(cells[2]),
                        "today": parse_int(cells[3]),
                    })
    # 历史记录去重计数，避免旧头部累计值漂移及重复执行的重复行。
    records = list({record["id"]: record for record in records}.values())
    records.sort(key=lambda record: (record["date"], record["type"]))
    if records:
        first = min(filter(None, [first] + [r["date"] for r in records]))
        last = max(filter(None, [last] + [r["date"] for r in records]))
        count = len(records)
        latest_total = next((r["total"] for r in reversed(records) if r["total"] is not None), None)
        if latest_total is not None:
            total = latest_total
    count = count or 0
    return {
        "repo": repo, "url": url or f"https://github.com/{repo}", "lang": lang,
        "cat": cat, "tagline": tagline, "desc": desc, "field": "",
        "total": total, "first": first, "last": last, "count": count,
        "records": records, "src": "archive",
    }


def collect_projects():
    out = {}
    if not LIB.exists():
        return out
    for f in LIB.rglob("*.md"):
        if f.name.startswith("_索引"):
            continue
        p = parse_archive(f)
        if p:
            out[p["repo"]] = p
    return out


# ---------------------------------------------------------------------------
# 四、汇总构建
# ---------------------------------------------------------------------------

def build_db():
    files = sorted(ANALYSIS.glob("GitHub热点日报_*.html"))
    weeklies = sorted(ANALYSIS.glob("GitHub热点周报_*.html"))
    monthlies = sorted(ANALYSIS.glob("GitHub热点月报_*.html"))
    files += weeklies + monthlies

    days, logs, skipped = [], [], []
    for f in files:
        day, note = parse_report(f)
        if day is None:
            skipped.append(note)
        else:
            days.append(day)
            logs.append(note)
    days.sort(key=lambda x: (x["date"], x["type"]))
    counters = {"daily": 0, "weekly": 0, "monthly": 0}
    for day in days:
        counters[day["type"]] += 1
        day["issue"] = counters[day["type"]]

    ai_days = collect_ai_days()
    projects = collect_projects()

    # 双源合并：档案为权威；期数据反推兜底（档案缺失的项目）
    derived = {}
    for d in days:
        if d["type"] == "monthly":  # 月报是本地聚合，不追加为官方上榜记录。
            continue
        for p in d["projects"]:
            r = derived.setdefault(p["repo"], {
                "repo": p["repo"], "url": p["url"], "lang": p.get("lang", ""),
                "cat": p.get("cat", ""), "tagline": p.get("tagline", ""),
                "desc": p.get("desc", ""), "field": "",
                "total": None, "first": d["date"], "last": d["date"], "count": 0,
                "records": [], "src": "issues"})
            r["count"] += 1
            if d["date"] > r["last"]:
                r["last"] = d["date"]
            r["records"].append({"date": d["date"], "rank": p["rank"], "total": p["total"], "today": p["today"],
                                 "type": d["type"], "period": d["period"], "id": d["id"],
                                 "rank_label": ("W#" if d["type"] == "weekly" else "#") + str(p["rank"])})
            if p.get("total") is not None:
                r["total"] = p["total"]
            for k in ("tagline", "desc", "cat", "lang"):
                if p.get(k) and not r[k]:
                    r[k] = p[k]
    merged = dict(projects)
    for repo, r in derived.items():
        if repo not in merged:
            merged[repo] = r
            continue
        archive = merged[repo]
        for key in ("tagline", "desc", "cat", "lang", "field"):
            if not archive.get(key) and r.get(key):
                archive[key] = r[key]
        # 同周期优先档案，补入报告中存在、档案尚未记载的周期。
        records = {record["id"]: record for record in r["records"]}
        records.update({record["id"]: record for record in archive["records"]})
        archive["records"] = sorted(records.values(), key=lambda record: (record["date"], record["type"]))
        archive["count"] = len(archive["records"])
        archive["first"] = min(filter(None, [archive["first"], r["first"]]))
        archive["last"] = max(filter(None, [archive["last"], r["last"]]))
        archive["total"] = next((record["total"] for record in reversed(archive["records"])
                                 if record["total"] is not None), archive["total"])

    n_projects = sum(len(d["projects"]) for d in days)
    db = {
        "generated_at": date.today().isoformat(),
        "meta": {
            "count_days": len(days),
            "count_daily": sum(1 for d in days if d["type"] == "daily"),
            "count_weekly": counters["weekly"],
            "count_monthly": counters["monthly"],
            "count_backfill": sum(1 for d in days if d["backfill"]),
            "count_skipped": len(skipped),
            "pdf_files": sorted(path.relative_to(ANALYSIS).as_posix() for path in ANALYSIS.rglob("*")
                                if path.is_file() and path.suffix.lower() == ".pdf"),
            "count_projects": n_projects,
            "count_repos": len({p["repo"] for d in days for p in d["projects"]}),
            "count_archives": len(projects),
            "count_ai_days": len(ai_days),
            "span": [days[0]["date"], days[-1]["date"]] if days else [],
        },
        "issues": days,
        "ai_days": ai_days,
        "projects": merged,
    }
    return db, logs, skipped


# ---------------------------------------------------------------------------
# 五、杂志页 HTML（Businessweek 大字报风 · 融合版 · 单文件自包含）
# ---------------------------------------------------------------------------
SHELL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#111111">
<title>GitHub 热点杂志 · GH WEEKLY · 每日项目推送总览刊</title>
<script>
if(location.protocol==='http:' || location.protocol==='https:'){
  var magazinePath=decodeURI(location.pathname),magazineMarker='/GitHub项目分析/';
  var magazineAt=magazinePath.lastIndexOf(magazineMarker);
  var magazineBase=magazineAt>=0?magazinePath.slice(0,magazineAt+1):new URL('.',location.href).pathname;
  window.ghDailyBase=new URL(magazineBase,location.origin).href;
  [['manifest','manifest.webmanifest'],['stylesheet','app.css']].forEach(function(item){
    var link=document.createElement('link');link.rel=item[0];link.href=new URL(item[1],window.ghDailyBase).href;document.head.appendChild(link);
  });
}
</script>
<style>
:root{
  --paper:#f5f2ea; --ink:#111111; --grey:#6d6a61; --line:#d8d2c2;
  --neon:#00b95c; --neon-dark:#009145; --red:#e8232a;
  --purple:#5b46b6; --purple-bg:#f5f1fc; --purple-line:#d9cdf2;
  --side-w:268px;
  --disp:"Arial Black","Avenir Next Condensed","Helvetica Neue",Impact,sans-serif;
  --cn:"PingFang SC","Heiti SC","Source Han Sans SC","Microsoft YaHei",sans-serif;
  --mono:"SF Mono",ui-monospace,Menlo,Consolas,"Courier New",monospace;
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font-family:var(--cn);-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
:focus-visible{outline:3px solid var(--neon-dark);outline-offset:4px}
[role="button"]:focus-visible{outline-offset:-3px}
::selection{background:var(--neon);color:#fff}

/* ---------- 侧边栏 ---------- */
#side{position:fixed;left:0;top:0;bottom:0;width:var(--side-w);background:#0c0c0c;color:#f2efe6;
  display:flex;flex-direction:column;z-index:50;transition:transform .28s cubic-bezier(.7,0,.3,1);overflow:hidden}
body.side-off #side{transform:translateX(-100%)}
#side .brand{padding:24px 20px 16px;border-bottom:1px solid #2a2a2a;cursor:pointer}
#side .brand .k1{font-family:var(--disp);font-size:33px;line-height:.95;letter-spacing:-1px;color:#fff}
#side .brand .k1 b{color:var(--neon)}
#side .brand .k2{font-size:10.5px;letter-spacing:.3em;color:#9a9a92;margin-top:8px}
#side .meta{padding:13px 20px;border-bottom:1px solid #2a2a2a;font-family:var(--disp);font-size:11px;color:#9a9a92;letter-spacing:.04em;line-height:1.7}
#side .meta b{color:var(--neon);font-size:19px}
#nav{flex:1;overflow-y:auto;padding:8px 0 16px;scrollbar-width:thin;scrollbar-color:#333 #0c0c0c}
#nav::-webkit-scrollbar{width:4px}
#nav::-webkit-scrollbar-thumb{background:#333}
.grp{margin-top:5px}
.grp-h{display:flex;align-items:center;gap:8px;padding:8px 20px;font-size:12px;font-weight:700;letter-spacing:.2em;color:#cfcac0;cursor:pointer;user-select:none}
.grp-h:hover{color:var(--neon)}
.grp-h .arr{font-size:9px;transition:transform .2s;color:#78766e}
.grp.open .grp-h .arr{transform:rotate(90deg)}
.grp-b{display:none}
.grp.open .grp-b{display:block}
.sub{padding:5px 20px 5px 32px;font-size:12.5px;color:#a5a29a;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:6px}
.sub:hover{color:#fff;background:#161616}
.sub.on{color:var(--neon);font-weight:700}
.sub .n{font-family:var(--disp);font-size:10px;color:#66645c;flex-shrink:0}
.sub2{padding:4px 20px 4px 46px;font-size:12px;color:#85837b;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sub2:hover{color:#fff}
.sub2.on{color:var(--neon)}
.grp-h.purple:hover{color:#b9a8e8}
#searchbar{padding:13px 16px;border-top:1px solid #2a2a2a}
#searchbar input{width:100%;background:#181818;border:1px solid #333;color:#f2efe6;border-radius:3px;
  padding:9px 12px;font-size:13px;font-family:var(--cn);outline:none}
#searchbar input:focus{border-color:var(--neon)}
#searchbar .hint{font-size:10px;color:#66645c;margin-top:6px;letter-spacing:.08em}

#side-toggle{position:fixed;left:var(--side-w);top:18px;z-index:60;width:30px;height:58px;
  background:var(--neon);color:#04150b;border:none;cursor:pointer;font-size:15px;font-weight:900;
  transition:left .28s cubic-bezier(.7,0,.3,1);box-shadow:2px 2px 0 rgba(0,0,0,.35)}
#side-toggle:hover{background:#fff}
body.side-off #side-toggle{left:0}

/* ---------- 主区 ---------- */
#main{margin-left:var(--side-w);transition:margin-left .28s cubic-bezier(.7,0,.3,1);min-height:100vh}
body.side-off #main{margin-left:0}
.wrap{max-width:1020px;margin:0 auto;padding:0 44px 90px}

.mast{display:flex;align-items:flex-end;justify-content:space-between;padding:40px 0 16px;border-bottom:4px solid var(--ink)}
.mast>div:first-child{min-width:0;flex:1}
.mast .kicker{font-size:11px;font-weight:800;letter-spacing:.3em;color:var(--grey);text-transform:uppercase;margin-bottom:9px}
.mast .kicker b{background:var(--ink);color:var(--paper);padding:2px 7px;margin-right:6px}
.mast .kicker b.p{background:var(--purple)}
.mast .brandline{font-size:12.5px;font-weight:700;color:var(--ink);margin-top:7px;letter-spacing:.05em}
.mast .brandline i{font-style:normal;background:var(--neon);color:#04150b;padding:1px 7px;font-weight:800;margin-right:7px;letter-spacing:.1em}
.mast .brandline i.p{background:var(--purple);color:#fff}
.mast h1{font-family:var(--disp);font-size:clamp(34px,5vw,72px);line-height:1.02;letter-spacing:-2px;font-weight:900;overflow-wrap:anywhere}
.mast h1 .d{display:block}
.home-mast h1{font-size:clamp(32px,4.3vw,66px)}
.mast .side-info{text-align:right;flex-shrink:0;padding-left:20px}
.mast .issue-no{font-family:var(--disp);font-size:14px;letter-spacing:.04em}
.mast .issue-no b{color:var(--neon-dark);font-size:25px}
.mast .wd{font-size:12.5px;color:var(--grey);margin-top:6px;letter-spacing:.18em}
.badge-backfill{display:inline-block;background:var(--red);color:#fff;font-size:11px;font-weight:800;
  letter-spacing:.14em;padding:3px 9px;margin-left:8px;vertical-align:middle;transform:translateY(-3px)}

/* 补档提示条 */
.bf-note{margin:22px 0 0;border:2px dashed var(--red);background:#fdf0ef;padding:13px 18px;font-size:12.5px;line-height:1.75;color:#7c1a1e}
.bf-note b{font-weight:800}
.bf-note a{color:var(--red);font-weight:700;text-decoration:underline}

/* AI 速递 */
.aiband{margin:26px 0 0;background:var(--purple-bg);border:2px solid var(--purple);padding:20px 24px 14px}
.aiband .bh{display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:8px}
.aiband h2{font-size:17px;color:var(--purple);letter-spacing:.02em}
.aiband .bn{font-size:11px;color:#8a7ab8}
.aiband ul{list-style:none;margin-top:6px}
.aiband li{padding:8px 0;border-bottom:1px dashed var(--purple-line);font-size:13.5px;line-height:1.7}
.aiband li:last-child{border-bottom:none}
.aiband li b{color:var(--purple)}
.aiband li a{color:var(--purple);font-weight:700;border-bottom:1px solid var(--purple-line)}
.ai-more{display:inline-block;margin:8px 0 6px;background:var(--purple);color:#fff;border:none;
  font-family:var(--cn);font-size:12.5px;font-weight:700;padding:7px 16px;cursor:pointer;letter-spacing:.06em}
.ai-more:hover{background:#443190}
.ai-full{display:none;margin:10px 0 4px;border-top:2px solid var(--purple);padding-top:6px}
.ai-full.show{display:block}
.ai-full .sec h4{font-size:13.5px;color:var(--purple);margin:14px 0 4px;font-weight:800}

/* 风向摘要 */
.wind{margin:24px 0 0;border:2px solid var(--ink);padding:19px 24px;background:#fff;position:relative}
.wind .tag{position:absolute;top:-11px;left:18px;background:var(--ink);color:var(--paper);font-size:11px;
  font-weight:800;letter-spacing:.28em;padding:3px 10px}
.wind p{font-size:15px;line-height:1.85;color:#26231d}

/* 榜单条目 */
.entry{display:grid;grid-template-columns:130px 1fr;gap:0 26px;padding:25px 0 29px;border-bottom:1px solid var(--line)}
.e-body{min-width:0}
.entry .rank{font-family:var(--disp);font-size:74px;line-height:.8;font-weight:900;letter-spacing:-3px;padding-top:6px}
.entry:nth-child(-n+3) .rank{color:var(--neon-dark)}
.entry .rank small{display:block;font-family:var(--cn);font-size:10px;font-weight:800;letter-spacing:.28em;color:var(--grey);margin-top:10px}
.e-head{display:flex;align-items:center;flex-wrap:wrap;gap:10px 14px}
.e-name{font-family:var(--mono);font-size:20.5px;font-weight:700;word-break:break-all}
.e-name:hover{color:var(--neon-dark);text-decoration:underline;text-decoration-thickness:2.5px;text-underline-offset:5px}
.hot-badge{background:var(--red);color:#fff;font-family:var(--disp);font-size:11px;letter-spacing:.1em;padding:3px 8px;transform:skewX(-8deg)}
.lang-chip{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;color:var(--grey);font-weight:600}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block;flex-shrink:0}
.e-stats{display:flex;gap:22px;margin:9px 0 3px;font-family:var(--disp);font-size:15px;flex-wrap:wrap}
.e-stats .lb{font-family:var(--cn);font-size:11px;color:var(--grey);font-weight:600;margin-right:4px}
.e-stats .s2{color:var(--red)}
.e-tagline{font-size:16px;font-weight:800;margin:8px 0;line-height:1.55}
.e-desc{font-size:13.5px;line-height:1.9;color:#3c3a33}
.e-field{font-size:12.5px;color:var(--grey);margin-top:9px;line-height:1.7}
.e-cat{margin-top:10px}
.e-cat span{display:inline-block;background:var(--ink);color:var(--paper);font-size:11px;font-weight:700;letter-spacing:.05em;padding:3px 10px}
.e-cat span.new{background:var(--neon)}
.e-record{font-size:12px;color:var(--grey);margin-top:8px}
.e-record a{color:var(--neon-dark);font-weight:700}
.miss{color:var(--grey);font-style:italic}

/* 排行/统计 */
.board{margin:32px 0 8px}
.board h2{font-family:var(--disp);font-size:29px;letter-spacing:-.5px;margin-bottom:15px}
.board h2 b{color:var(--neon-dark)}
.board h2.p{color:var(--purple)}
.brow{display:grid;grid-template-columns:56px 1fr 180px;align-items:center;gap:14px;padding:10px 0;border-bottom:1px solid var(--line)}
.brow .r{font-family:var(--disp);font-size:23px;font-weight:900}
.brow .nm{font-family:var(--mono);font-size:14.5px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer}
.brow .nm:hover{color:var(--neon-dark)}
.brow .v{font-family:var(--disp);font-size:16px;text-align:right;white-space:nowrap}
.brow .v small{font-family:var(--cn);font-size:11px;color:var(--grey);margin-left:3px}
.bar{height:12px;background:var(--line);margin-top:5px;max-width:420px}
.bar i{display:block;height:100%;background:var(--neon)}

/* 首页刊架 */
.cover-grid{display:grid;grid-template-columns:1fr 330px;gap:22px;margin-top:32px}
.latest-card{background:var(--ink);color:var(--paper);padding:32px 30px;cursor:pointer;transition:background .15s}
.latest-card:hover{background:#000}
.latest-card .kk{font-size:11px;letter-spacing:.3em;color:var(--neon);font-weight:800;margin-bottom:15px}
.latest-card .big{font-family:var(--disp);font-size:clamp(30px,4.1vw,60px);line-height:1.05;letter-spacing:-1px;overflow-wrap:anywhere}
.latest-card .sub1{font-size:13.5px;color:#b9b5aa;margin-top:13px;line-height:1.75}
.latest-card .sub1 b{color:#fff}
.stat-card{background:#fff;border:2px solid var(--ink);padding:20px 24px}
.stat-card .row{display:flex;justify-content:space-between;align-items:baseline;padding:8px 0;border-bottom:1px dashed var(--line)}
.stat-card .row:last-child{border-bottom:none}
.stat-card .k{font-size:12.5px;color:var(--grey);font-weight:600}
.stat-card .v{font-family:var(--disp);font-size:23px;font-weight:900}
.stat-card .v.g{color:var(--neon-dark)}
.cat-wall{margin-top:38px}
.cat-wall h3{font-family:var(--disp);font-size:21px;margin-bottom:13px}
.cat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:11px}
.cat-cell{border:2px solid var(--ink);padding:15px 16px 13px;cursor:pointer;background:#fff;transition:all .15s}
.cat-cell:hover{background:var(--ink);color:var(--paper)}
.cat-cell:hover .cc-n{color:var(--neon)}
.cat-cell .cc-n{font-family:var(--disp);font-size:29px;font-weight:900;color:var(--neon-dark)}
.cat-cell .cc-t{font-size:13px;font-weight:700;margin-top:4px}
.more-btn{display:block;width:100%;margin:18px 0;padding:12px;background:none;border:2px solid var(--ink);
  font-family:var(--cn);font-size:13.5px;font-weight:800;cursor:pointer;letter-spacing:.1em}
.more-btn:hover{background:var(--ink);color:var(--paper)}

/* 书架/详情/搜索 */
.shelf-h{font-family:var(--disp);font-size:38px;letter-spacing:-1px;margin:40px 0 6px;line-height:1.05}
.shelf-h b{color:var(--neon-dark)}
.shelf-h.p b{color:var(--purple)}
.shelf-sub{color:var(--grey);font-size:13px;margin-bottom:8px}
.shelf-list .entry{grid-template-columns:100px 1fr}
.shelf-list .entry .rank{font-size:42px;letter-spacing:-2px}
.pj-head{padding:40px 0 18px;border-bottom:4px solid var(--ink)}
.pj-head .kicker{font-size:11px;font-weight:800;letter-spacing:.3em;color:var(--grey);margin-bottom:8px;text-transform:uppercase}
.pj-head h1{font-family:var(--mono);font-size:clamp(25px,4.2vw,42px);font-weight:800;word-break:break-all}
.pj-head h1 a:hover{color:var(--neon-dark)}
.pj-meta{display:flex;flex-wrap:wrap;gap:8px 24px;margin-top:13px;font-size:13px;color:var(--grey)}
.pj-meta b{color:var(--ink)}
.timeline{margin-top:34px;overflow-x:auto}
.timeline h2{font-family:var(--disp);font-size:25px;margin-bottom:13px}
.tl-table{width:100%;border-collapse:collapse;background:#fff;border:2px solid var(--ink)}
.tl-table th{background:var(--ink);color:var(--paper);font-size:12px;letter-spacing:.14em;padding:10px 14px;text-align:left}
.tl-table td{padding:10px 14px;border-bottom:1px solid var(--line);font-size:13.5px}
.tl-table tr:hover td{background:#f0ede2;cursor:pointer}
.tl-table .d{font-family:var(--disp);font-size:13.5px}
.tl-table .up{color:var(--red);font-weight:700}
.tl-table .dn{color:var(--neon-dark);font-weight:700}
.sr-count{font-family:var(--disp);font-size:15px;margin:28px 0 2px}
.empty{padding:66px 0;text-align:center;color:var(--grey);font-size:15px}
.empty .big{font-family:var(--disp);font-size:40px;display:block;margin-bottom:13px;color:var(--ink)}

/* AI 日报整页视图 */
.aiwrap .sec{margin:26px 0}
.aiwrap .sec h3{font-size:16px;font-weight:800;color:var(--purple);border-left:5px solid var(--purple);padding-left:11px;margin-bottom:8px}
.aiwrap li{list-style:none;padding:10px 0;border-bottom:1px dashed var(--purple-line);font-size:14px;line-height:1.8}
.aiwrap li b{color:var(--purple)}
.aiwrap li a{color:var(--purple);font-weight:700;border-bottom:1px solid var(--purple-line)}
.srcfile{font-size:11.5px;color:var(--grey);margin-top:16px}

/* 关于页 */
.about p{font-size:14.5px;line-height:2;margin:14px 0;max-width:780px}
.about h3{font-family:var(--disp);font-size:22px;margin:30px 0 6px}
.about .quote{border-left:5px solid var(--neon);background:#fff;padding:16px 20px;font-size:15px;line-height:1.95;margin:18px 0}
.about ul{margin:10px 0 10px 22px;font-size:14px;line-height:2;color:#33302a}
.about a{color:var(--neon-dark);font-weight:700;border-bottom:1.5px solid var(--neon)}

/* 周月入口 */
.wk-entry{display:flex;justify-content:space-between;align-items:center;border:2px solid var(--ink);background:#fff;
  padding:16px 20px;margin:12px 0;cursor:pointer;transition:background .15s}
.wk-entry:hover{background:var(--ink);color:var(--paper)}
.wk-entry .t{font-family:var(--disp);font-size:19px}
.wk-entry .s{font-size:12.5px;color:var(--grey)}
.wk-entry:hover .s{color:#cfcac0}

.foot{margin-top:56px;padding-top:16px;border-top:4px solid var(--ink);display:flex;justify-content:space-between;
  font-size:11.5px;color:var(--grey);letter-spacing:.05em;flex-wrap:wrap;gap:8px}
.foot b{color:var(--ink)}
.foot a{color:var(--neon-dark);font-weight:700}

@media (max-width:900px){
  #side{width:min(268px,calc(100vw - 44px));transform:translateX(-100%)}
  body.side-on #side{transform:translateX(0)}
  #side-toggle{left:0!important}
  #main{margin-left:0!important}
  .wrap{padding:0 20px 70px}
  .entry{grid-template-columns:68px 1fr;gap:0 14px}
  .entry .rank{font-size:38px;letter-spacing:-1px}
  .shelf-list .entry .rank{font-size:32px}
  .cover-grid{grid-template-columns:1fr}
  .mast{flex-wrap:wrap;gap:18px;padding-top:90px}
  .mast>div:first-child{flex-basis:100%}
  .mast .side-info{text-align:left;padding-left:0}
  .brow{grid-template-columns:42px 1fr 130px}
}
@media (max-width:480px){
  .mast h1,.home-mast h1{font-size:clamp(29px,8.4vw,39px);letter-spacing:-1px}
  .brandline{line-height:1.8}
  .shelf-list .entry,.entry{grid-template-columns:42px minmax(0,1fr);gap:0 12px}
  .entry .rank,.shelf-list .entry .rank{font-size:28px}
  .e-name{font-size:16px}
  .e-stats{gap:6px 14px}
  .brow{grid-template-columns:26px minmax(0,1fr) 98px;gap:8px}
  .brow .nm{font-size:12px}
  .brow .v{font-size:13px}
  .latest-card{padding:26px 22px}
  .latest-card .big{font-size:clamp(27px,8.4vw,38px)}
  .aiband,.wind{padding-left:16px;padding-right:16px}
  .tl-table{min-width:560px}
}
</style>
</head>
<body class="">

<aside id="side">
  <div class="brand" onclick="go('#/')">
    <div class="k1">GH<br><b>WEEKLY</b></div>
    <div class="k2">GITHUB 热点杂志</div>
  </div>
  <div class="meta">已收录 <b>__N_DAYS__</b> 期<br>__N_REPOS__ 项目 · __N_ITEMS__ 条记录</div>
  <nav id="nav"></nav>
  <div id="searchbar">
    <input id="q" type="search" aria-label="搜索项目、语言、描述或分类" placeholder="搜索项目 / 语言 / 描述…" autocomplete="off">
    <div class="hint">即时搜索 · ESC 清空</div>
  </div>
</aside>
<button id="side-toggle" title="收起 / 展开目录" aria-label="收起或展开目录" aria-controls="side" aria-expanded="true">☰</button>

<main id="main"><div class="wrap" id="view" tabindex="-1"></div></main>

<script type="application/json" id="DB">__DB__</script>
<script>
(function(){
"use strict";
var DB = JSON.parse(document.getElementById('DB').textContent);
var ISSUES = DB.issues, AID = DB.ai_days, PROJ = DB.projects, META = DB.meta;
var view = document.getElementById('view');
var esc = function(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); };
var fmt = function(n){ return n==null?'—':Number(n).toLocaleString('en-US'); };
function safeURL(value){ try{ var url=new URL(value);return /^(https?:)$/.test(url.protocol)?url.href:''; }catch(e){ return ''; } }
function encodePart(value){return encodeURIComponent(value).replace(/'/g,'%27');}
function decodePart(value){try{return decodeURIComponent(value);}catch(e){return '';}}
function sourceHTML(item){
  var sources=item.sources&&item.sources.length?item.sources:(item.url?[{url:item.url,src:item.src}]:[]);
  return sources.map(function(source){ var url=safeURL(source.url);return url?' <a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">['+esc(source.src||'来源')+']</a>':''; }).join('');
}
var dailies = ISSUES.filter(function(d){ return d.type==='daily'; });
var latest = dailies[dailies.length-1] || null;

/* 派生索引 */
var byWeek = {}, byMonth = {}, byRepo = {}, byCat = {};
dailies.forEach(function(d){
  (byWeek[d.week] = byWeek[d.week] || []).push(d);
  (byMonth[d.month] = byMonth[d.month] || []).push(d);
  d.projects.forEach(function(p){
    var r = byRepo[p.repo] = byRepo[p.repo] || {repo:p.repo, records:[], count:0, maxTotal:0};
    r.count++;
    r.records.push({date:d.date, rank:p.rank, today:p.today, total:p.total});
    if(p.total != null && p.total > (r.maxTotal||0)) r.maxTotal = p.total;
  });
});
Object.keys(byRepo).forEach(function(k){ byRepo[k].records.sort(function(a,b){ return a.date<b.date?-1:1; }); });
var PKEYS = Object.keys(PROJ);
PKEYS.forEach(function(k){
  var c0 = (PROJ[k].cat||'').split('›')[0].trim() || '未分类';
  (byCat[c0] = byCat[c0] || []).push(PROJ[k]);
});
var CATS = Object.keys(byCat).sort();
var aiDates = Object.keys(AID).sort().reverse();

/* 侧边栏 */
function grp(id, title, open, body, purple){ return '<div class="grp'+(open?' open':'')+'" id="'+id+'"><div class="grp-h'+(purple?' purple':'')+'" aria-expanded="'+open+'" onclick="toggleGrp(\''+id+'\')">▸ '+title+'</div><div class="grp-b">'+body+'</div></div>'; }
function sub(hash, t, n){ return '<div class="sub" onclick="go(\''+esc(hash)+'\')"><span>'+esc(t)+'</span>'+(n?'<span class="n">'+esc(n)+'</span>':'')+'</div>'; }
function sub2(hash, t){ return '<div class="sub2" onclick="go(\''+hash+'\')">'+esc(t)+'</div>'; }
function issueLabel(d){ return '第 '+String(d.issue).padStart(3,'0')+' 期'; }
function issueKind(d){ return d.type==='weekly'?'周刊':d.type==='monthly'?'月刊':'日刊'; }
function buildNav(){
  var h = '';
  h += grp('g-latest','今日刊', true, latest?sub('#/day/'+latest.date, latest.date, issueLabel(latest)):'<div class="sub">暂无日报</div>');
  var months = Object.keys(byMonth).sort().reverse(), mb = '';
  months.forEach(function(mo){
    var ds = byMonth[mo].slice().reverse();
    mb += sub('#/month/'+mo, '▦ '+mo, ds.length+' 期');
    ds.forEach(function(d){ mb += sub2('#/day/'+d.date, issueLabel(d)+' · '+d.date+(d.backfill?' 🗂':'')); });
  });
  h += grp('g-days','日报归档', true, mb);
  var wb = '';
  var weeks=Object.keys(byWeek);
  ISSUES.forEach(function(d){if(d.type==='weekly'&&weeks.indexOf(d.period)<0)weeks.push(d.period);});
  weeks.sort().reverse().forEach(function(w){ wb += sub('#/week/'+w, w, (byWeek[w]||[]).length+' 期日报'); });
  h += grp('g-weeks','周合集', false, wb);
  var mob = '';
  var allMonths=months.slice();
  ISSUES.forEach(function(d){if(d.type==='monthly'&&allMonths.indexOf(d.period)<0)allMonths.push(d.period);});
  allMonths.sort().reverse().forEach(function(mo){ mob += sub('#/month/'+mo, mo, (byMonth[mo]||[]).length+' 期日报'); });
  h += grp('g-months','月特辑', false, mob);
  var ab = '';
  aiDates.forEach(function(dt){ ab += '<div class="sub" style="color:#b9a8e8" onclick="go(\'#/ai/'+dt+'\')"><span>'+dt+'</span><span class="n">'+aiCount(AID[dt])+' 条</span></div>'; });
  if(!ab) ab = '<div class="sub" style="cursor:default">暂无 AI 日报数据</div>';
  h += grp('g-ai','⚡ AI 前沿', false, ab, true);
  var cb = '';
  CATS.forEach(function(c){ cb += sub('#/cat/'+encodePart(c), c, byCat[c].length); });
  h += grp('g-cats','分类书架', false, cb);
  h += grp('g-about','关于本刊', false, '<div class="sub" onclick="go(\'#/about\')">关于 · 数据口径</div>');
  document.getElementById('nav').innerHTML = h;
  ['g-latest','g-days','g-weeks','g-months','g-ai','g-cats','g-about'].forEach(function(id){
    try{ if(localStorage.getItem('ghm-'+id)==='0'){ var el=document.getElementById(id); if(el){el.classList.remove('open');el.querySelector('.grp-h').setAttribute('aria-expanded','false');} } }catch(e){}
  });
  enableKeyboard(document.getElementById('side'));
}
window.toggleGrp = function(id){
  var el = document.getElementById(id);
  el.classList.toggle('open');
  el.querySelector('.grp-h').setAttribute('aria-expanded',el.classList.contains('open')?'true':'false');
  try{ localStorage.setItem('ghm-'+id, el.classList.contains('open')?'1':'0'); }catch(e){}
};

/* 组件 */
function langDot(lang){
  var colors = {TypeScript:'#3178c6',JavaScript:'#f1e05a',Python:'#3572A5',Rust:'#dea584',Go:'#00ADD8',
    'C':'#555','C++':'#f34b7d','C#':'#178600',Java:'#b07219',Shell:'#89e051',HTML:'#e34c26',CSS:'#563d7c',
    Vue:'#41b883',Svelte:'#ff3e00',Zig:'#ec915c',Lua:'#000080',Ruby:'#701516',PHP:'#4F5D95',
    Swift:'#F05138',Kotlin:'#A97BFF',Dart:'#00B4AB','Jupyter Notebook':'#DA5B0B',Nix:'#7e7eff',
    Elixir:'#6e4a7e',Haskell:'#5e5086',OCaml:'#3be133',Solidity:'#AA6746',Astro:'#ff5a03'};
  var c = colors[lang] || '#999';
  return '<span class="lang-chip"><span class="dot" style="background:'+c+'"></span>'+esc(lang||'未知')+'</span>';
}
function aiCount(day){ return day.sections.reduce(function(a,s){ return a+s.items.length; },0); }
function aiItemsHTML(items){
  return '<ul>'+items.map(function(it){
    return '<li><b>'+esc(it.t)+'</b>'+(it.d?' — '+esc(it.d):'')
      +sourceHTML(it)+'</li>';
  }).join('')+'</ul>';
}
function aiBandHTML(d){
  var band = '';
  if(d.ai && d.ai.length){
    band += '<div class="aiband"><div class="bh"><h2>⚡ AI 前沿速递</h2><span class="bn">融合板块 · 全球 AI 动态精选</span></div>'
      + '<ul>'+d.ai.map(function(it){
          return '<li><b>'+esc(it.t)+'</b>'+(it.d?'：'+esc(it.d):'')
            +sourceHTML(it)+'</li>';
        }).join('')+'</ul>';
    var full = AID[d.date];
    if(full){
      band += '<button class="ai-more" onclick="var f=document.getElementById(\'aifull\');f.classList.toggle(\'show\');this.textContent=f.classList.contains(\'show\')?\'收起完整版 ▴\':\'查看当日完整 AI 日报 ▾\';">查看当日完整 AI 日报 ▾</button>'
        + '<div class="ai-full" id="aifull">'
        + full.sections.map(function(s){ return '<div class="sec"><h4>'+esc(s.title)+'</h4>'+aiItemsHTML(s.items)+'</div>'; }).join('')
        + '</div>';
    }
    band += '</div>';
  } else if(AID[d.date]){
    var f2 = AID[d.date];
    band += '<div class="aiband"><div class="bh"><h2>⚡ AI 前沿速递</h2><span class="bn">当日共 '+aiCount(f2)+' 条</span></div>'
      + f2.sections.map(function(s){ return '<div style="margin:10px 0 2px"><b style="font-size:13px;color:#8a7ab8">'+esc(s.title)+'</b>'+aiItemsHTML(s.items)+'</div>'; }).join('')
      + '</div>';
  }
  return band;
}
function bfNoteHTML(d){
  if(!d.backfill) return '';
  return '<div class="bf-note"><b>🗂 本期为补档重建</b>——历史日报记录未收录，数据来自 Wayback Machine 快照'
    + (d.snapshot?'（快照于 <b>'+esc(d.snapshot)+'</b>）':'')
    + (d.snapshot_url?' <a href="'+esc(d.snapshot_url)+'" target="_blank" rel="noopener">查看原始快照 ↗</a>':'')
    + '。星数为快照时点数据；部分描述保留快照中的英文原文。</div>';
}
function entryHTML(p, d){
  var pr = PROJ[p.repo] || byRepo[p.repo];
  var cnt = pr ? (pr.records||[]).filter(function(rec){return rec.date<=d.date;}).length : 0;
  var firstTime = false, recNote = '';
  if(pr){
    var recs = pr.records || [];
    if(pr.first===d.date){ firstTime = true; recNote = '🆕 本日首次收录'; }
    else{
      var prev = null;
      for(var i=0;i<recs.length;i++){ if(recs[i].date < d.date) prev = recs[i]; }
      recNote = '📈 截至本日收录 '+cnt+' 次上榜' + (prev ? '，上次 '+prev.date+' '+(prev.rank_label||'#'+(prev.rank||'—')) : '');
    }
  }
  var tl = pr && pr.records && pr.records.length ? '#/project/'+encodeURIComponent(p.repo) : '';
  return '<div class="entry">'
    + '<div class="rank">'+(p.rank<10?'0':'')+p.rank+'<small>RANK</small></div>'
    + '<div class="e-body">'
    +   '<div class="e-head"><a class="e-name" href="'+esc(safeURL(p.url))+'" target="_blank" rel="noopener noreferrer">'+esc(p.repo)+'</a>'
    +   (p.hot?'<span class="hot-badge">HOT ▲'+fmt(p.today)+'</span>':'')+langDot(p.lang)+'</div>'
    +   '<div class="e-stats"><span><span class="lb">★ 总星</span>'+fmt(p.total)+'</span>'
    +   '<span class="s2"><span class="lb">▲ '+(d.type==='weekly'?'本周':d.type==='monthly'?'记录增长':'今日')+'</span>'+(p.today==null?'暂未获取':'+'+fmt(p.today))+'</span>'
    +   (cnt?'<span><span class="lb">上榜</span>'+cnt+' 次</span>':'')+'</div>'
    +   (p.tagline?'<div class="e-tagline">'+esc(p.tagline)+'</div>':'')
    +   (p.desc?'<div class="e-desc">'+esc(p.desc)+'</div>':(p.tagline?'':'<div class="e-desc miss">描述暂未获取，点击项目名前往 GitHub 查看</div>'))
    +   (p.field?'<div class="e-field"><b>适用领域</b> · '+esc(p.field)+'</div>':'')
    +   '<div class="e-cat"><span'+(firstTime?' class="new"':'')+'>'+esc(p.cat||'未分类')+'</span></div>'
    +   (recNote?'<div class="e-record">'+recNote+(tl?' · <a href="'+tl+'">查看全部上榜记录 →</a>':'')+'</div>':'')
    + '</div></div>';
}
function mastHTML(d, kicker, big, purple){
  return '<div class="mast"><div>'
    + '<div class="kicker"><b'+(purple?' class="p"':'')+'>GH WEEKLY</b>'+(kicker||' DAILY ISSUE')+'</div>'
    + '<h1><span class="d"'+(purple?' style="color:var(--purple)"':'')+'>'+(big||d.date.replace(/-/g,'.'))+'</span></h1>'
    + '<div class="brandline"><i'+(purple?' class="p"':'')+'>GITHUB 每日项目推送</i>总览刊 · 融合 AI 前沿速递</div></div>'
    + '<div class="side-info"><div class="issue-no">'+issueKind(d)+'<br><b>'+issueLabel(d)+'</b></div>'
    + '<div class="wd">'+d.weekday+(d.backfill?'<span class="badge-backfill">🗂 补档</span>':'')+'</div></div></div>';
}
function footHTML(){
  return '<div class="foot"><span><b>GH WEEKLY</b> · GitHub 每日项目推送 · 总览刊 · 数据来自每日 Trending 日报与 AI 前沿采集</span>'
    + '<span>共 '+META.count_days+' 期 · 生成于 '+esc(DB.generated_at)+' · <a href="#/about">关于与数据口径</a></span></div>';
}

/* 视图 */
function vHome(){
  if(!latest)return '<div class="shelf-h">你的第一期<br><b>从这里开始</b></div><div class="board"><h2>这是你的本地刊物</h2><p class="shelf-sub">默认没有历史数据。第一次成功生成的日报为第 001 期，此后持续累积，重启不会重置。</p><p>你可以在 <a href="../settings.html" style="color:var(--neon-dark);text-decoration:underline">设置</a> 中选择第三方模型或 Ollama，再点击“立即采编”；也可以将自己的工作区交给已有 AI 工具采编，无需在本项目重复填写 API Key。</p><p class="shelf-sub">只想阅读作者的每日内容？<a href="https://0505ttt.github.io/github-daily-press/" target="_blank" rel="noopener noreferrer" style="text-decoration:underline">打开公开阅读网站</a>。</p></div>'+footHTML();
  var h = '<div class="mast home-mast"><div>'
    + '<div class="kicker"><b>GH WEEKLY</b> MAGAZINE RACK</div>'
    + '<h1><span class="d">OPEN SOURCE</span><span class="d" style="color:var(--neon-dark)">DAILY PRESS</span></h1>'
    + '<div class="brandline"><i>GITHUB 每日项目推送</i>总览刊 · 融合 AI 前沿速递</div></div>'
    + '<div class="side-info"><div class="issue-no">已出版<br><b>'+META.count_days+'</b> 期</div>'
    + '<div class="wd">'+(META.span[0]||'')+' → '+(META.span[1]||'')+'</div></div></div>';
  var latestAi = aiDates.length ? '<div class="row"><span class="k">AI 前沿日报</span><span class="v g">'+META.count_ai_days+' 天</span></div>' : '';
  h += '<div class="cover-grid">'
    + '<div class="latest-card" onclick="go(\'#/day/'+latest.date+'\')">'
    + '<div class="kk">▶ 最新日刊 · '+issueLabel(latest)+'</div>'
    + '<div class="big">'+latest.date.replace(/-/g,'.')+'</div>'
    + '<div class="sub1">'+latest.weekday+' · '+latest.projects.length+' 个项目'+((latest.ai&&latest.ai.length)?' · '+latest.ai.length+' 条 AI 速递':'')
    + (latest.projects[0]?'<br>头条：<b>'+esc(latest.projects[0].repo)+'</b> ▲'+fmt(latest.projects[0].today):'')
    + '<br>点击翻开本期杂志 →</div></div>'
    + '<div class="stat-card">'
    + '<div class="row"><span class="k">收录期数</span><span class="v g">'+META.count_days+'</span></div>'
    + '<div class="row"><span class="k">项目档案</span><span class="v">'+META.count_archives+'</span></div>'
    + '<div class="row"><span class="k">上榜记录</span><span class="v">'+META.count_projects+'</span></div>'
    + latestAi
    + '<div class="row"><span class="k">时间跨度</span><span class="v" style="font-size:14px">'+(META.span[0]||'').slice(5)+' — '+(META.span[1]||'').slice(5)+'</span></div>'
    + '</div></div>';
  var top = PKEYS.map(function(k){ return PROJ[k]; }).sort(function(a,b){ return (b.count||0)-(a.count||0); }).slice(0,6);
  h += '<div class="board"><h2>★ 常客榜 · 上榜次数 <b>TOP 6</b></h2>';
  top.forEach(function(r,i){
    h += '<div class="brow"><div class="r">'+(i+1)+'</div>'
      + '<div><div class="nm" onclick="go(\'#/project/'+encodeURIComponent(r.repo)+'\')">'+esc(r.repo)+'</div></div>'
      + '<div class="v">'+(r.count||0)+'<small>次上榜</small></div></div>';
  });
  h += '</div>';
  h += '<div class="cat-wall"><h3>分类书架 · '+CATS.length+' 个领域 · '+META.count_archives+' 份档案</h3><div class="cat-grid">';
  CATS.forEach(function(c){
    h += '<div class="cat-cell" onclick="go(\'#/cat/'+encodePart(c)+'\')">'
      + '<div class="cc-n">'+byCat[c].length+'</div><div class="cc-t">'+esc(c)+'</div></div>';
  });
  h += '</div></div>' + footHTML();
  return h;
}
function vDay(dateStr){
  var d = null;
  ISSUES.forEach(function(x){ if(x.date===dateStr && x.type==='daily') d = x; });
  if(!d) return '<div class="empty"><span class="big">404</span>未找到该期：'+esc(dateStr)+'</div>'+footHTML();
  var h = mastHTML(d);
  h += bfNoteHTML(d);
  h += aiBandHTML(d);
  if(d.wind) h += '<div class="wind"><span class="tag">本期风向</span><p>'+esc(d.wind)+'</p></div>';
  h += '<div class="list">';
  d.projects.forEach(function(p){ h += entryHTML(p, d); });
  h += '</div>' + footHTML();
  return h;
}
function vWeek(weekStr){
  var ds = (byWeek[weekStr]||[]).slice().sort(function(a,b){ return a.date<b.date?-1:1; });
  var wkIssue = ISSUES.find(function(issue){return issue.type==='weekly'&&issue.period===weekStr;});
  if(!ds.length) return wkIssue?vPeriodReport(wkIssue):'<div class="empty"><span class="big">404</span>未找到该周：'+esc(weekStr)+'</div>'+footHTML();
  var items = {}, order = [];
  ds.forEach(function(d){ d.projects.forEach(function(p){
    if(!items[p.repo]){ items[p.repo]={todaySum:0,count:0}; order.push(p.repo); }
    items[p.repo].todaySum += (p.today||0);
    items[p.repo].count++;
  });});
  order.sort(function(a,b){ return items[b].todaySum-items[a].todaySum; });
  var h = '<div class="mast"><div>'
    + '<div class="kicker"><b>GH WEEKLY</b> WEEKLY DIGEST</div>'
    + '<h1><span class="d">'+esc(weekStr)+'</span></h1>'
    + '<div class="brandline"><i>GITHUB 每日项目推送</i>本周合集</div></div>'
    + '<div class="side-info"><div class="issue-no">本周<br><b>'+ds.length+' 期</b></div>'
    + '<div class="wd">'+ds[0].date+' → '+ds[ds.length-1].date+'</div></div></div>';
  h += '<div class="board"><h2>▲ 本周星火榜 · 已收录日榜新增合计 <b>TOP 15</b></h2><p class="shelf-sub">仅累计本刊收录的日榜新增，缺失日及未上榜日不计入，不代表仓库整周净增长。</p>';
  var maxv = items[order[0]] ? items[order[0]].todaySum : 1;
  order.slice(0,15).forEach(function(repo,i){
    var it = items[repo];
    h += '<div class="brow"><div class="r">'+(i+1)+'</div>'
      + '<div><div class="nm" onclick="go(\'#/project/'+encodeURIComponent(repo)+'\')">'+esc(repo)+'</div>'
      + '<div class="bar"><i style="width:'+Math.round(100*it.todaySum/maxv)+'%"></i></div></div>'
      + '<div class="v">+'+fmt(it.todaySum)+'<small>·'+it.count+'次</small></div></div>';
  });
  h += '</div>';
  var weekAi = aiDates.filter(function(dt){ for(var i=0;i<ds.length;i++) if(ds[i].date===dt) return true; return false; });
  if(weekAi.length){
    h += '<div class="board"><h2 class="p">⚡ 本周 AI 大事件回顾</h2><div class="aiwrap">';
    weekAi.forEach(function(dt){
      var f = AID[dt];
      f.sections.forEach(function(s){
        if(/大模型|Agent|工程|动态/.test(s.title)){
          h += '<div class="sec"><h3>'+esc(s.title)+'（'+dt+'）</h3>'+aiItemsHTML(s.items.slice(0,5))+'</div>';
        }
      });
    });
    h += '</div></div>';
  }
  h += '<div class="board"><h2>▤ 本周各期</h2>';
  ds.forEach(function(d){
    h += '<div class="brow"><div class="r" style="font-size:14px">'+d.date.slice(5)+'</div>'
      + '<div><div class="nm" onclick="go(\'#/day/'+d.date+'\')">'+issueLabel(d)+' · '+d.projects.length+' 个项目 · 头条 '+esc(d.projects[0].repo)+'</div></div>'
      + '<div class="v">'+(d.backfill?'🗂 补档':'')+'</div></div>';
  });
  h += '</div>';
  if(wkIssue){
    h += '<a class="wk-entry" href="'+esc(wkIssue.file)+'" target="_blank" rel="noopener"><div><div class="t">📄 本周周报原件</div><div class="s">'+esc(wkIssue.file)+' · 完整榜单</div></div><div>↗</div></a>';
  }
  return h + footHTML();
}
function vMonth(monthStr){
  var ds = (byMonth[monthStr]||[]).slice().sort(function(a,b){ return a.date<b.date?-1:1; });
  var moIssue = ISSUES.find(function(issue){return issue.type==='monthly'&&issue.period===monthStr;});
  if(!ds.length) return moIssue?vPeriodReport(moIssue):'<div class="empty"><span class="big">404</span>未找到该月：'+esc(monthStr)+'</div>'+footHTML();
  var items = {};
  ds.forEach(function(d){ d.projects.forEach(function(p){
    var it = items[p.repo] = items[p.repo]||{count:0,todaySum:0};
    it.count++; it.todaySum += (p.today||0);
  });});
  var order = Object.keys(items).sort(function(a,b){ return items[b].count-items[a].count || items[b].todaySum-items[a].todaySum; });
  var newRepos = order.filter(function(r){ return PROJ[r]&&PROJ[r].first&&PROJ[r].first.slice(0,7)===monthStr; });
  var h = '<div class="mast"><div>'
    + '<div class="kicker"><b>GH WEEKLY</b> MONTHLY SPECIAL</div>'
    + '<h1><span class="d">'+monthStr.replace('-','/')+'</span></h1>'
    + '<div class="brandline"><i>GITHUB 每日项目推送</i>月度特辑</div></div>'
    + '<div class="side-info"><div class="issue-no">本月<br><b>'+ds.length+' 期</b></div>'
    + '<div class="wd">'+order.length+' 个项目 · '+newRepos.length+' 个新面孔</div></div></div>';
  h += '<div class="board"><h2>★ 本月常客 · 日榜上榜次数 <b>TOP 12</b></h2><p class="shelf-sub">新增合计只覆盖收录日，不等于整月净增长；新面孔以档案首次收录日期为准。</p>';
  order.slice(0,12).forEach(function(r,i){
    h += '<div class="brow"><div class="r">'+(i+1)+'</div>'
      + '<div><div class="nm" onclick="go(\'#/project/'+encodeURIComponent(r)+'\')">'+esc(r)+'</div></div>'
      + '<div class="v">'+items[r].count+'<small>次 · +'+fmt(items[r].todaySum)+'</small></div></div>';
  });
  h += '</div><div class="board"><h2>▤ 本月各期</h2>';
  ds.forEach(function(d){
    h += '<div class="brow"><div class="r" style="font-size:14px">'+d.date.slice(5)+'</div>'
      + '<div><div class="nm" onclick="go(\'#/day/'+d.date+'\')">'+issueLabel(d)+' · 头条 '+esc(d.projects[0].repo)+' ▲'+fmt(d.projects[0].today)+'</div></div>'
      + '<div class="v">'+d.projects.length+'<small>项目</small></div></div>';
  });
  h += '</div>';
  if(moIssue){
    h += '<a class="wk-entry" href="'+esc(moIssue.file)+'" target="_blank" rel="noopener"><div><div class="t">📄 本月月报原件</div><div class="s">'+esc(moIssue.file)+'</div></div><div>↗</div></a>';
  }
  return h + footHTML();
}
function vPeriodReport(issue){
  var h=mastHTML(issue,issue.type==='weekly'?'WEEKLY ISSUE':'MONTHLY ISSUE',esc(issue.period));
  if(issue.wind)h+='<div class="wind"><span class="tag">本期概览</span><p>'+esc(issue.wind)+'</p></div>';
  h+='<div class="list">'+issue.projects.map(function(project){return entryHTML(project,issue);}).join('')+'</div>';
  return h+footHTML();
}
var CAT_LIMIT = 60;
function catSlice(list, from){
  var h = '';
  list.slice(from, from+CAT_LIMIT).forEach(function(r,i){
    var idx = from+i;
    var last = (r.records&&r.records.length) ? r.records[r.records.length-1].date : (r.last||'');
    h += '<div class="entry"><div class="rank">'+(idx<9?'0':'')+(idx+1)+'<small>'+(r.count||0)+' 次</small></div>'
      + '<div class="e-body"><div class="e-head"><a class="e-name" href="#/project/'+encodeURIComponent(r.repo)+'">'+esc(r.repo)+'</a>'+langDot(r.lang)+'</div>'
      + '<div class="e-stats"><span><span class="lb">★ 总星</span>'+fmt(r.total!=null?r.total:(r.maxTotal||null))+'</span>'
      + '<span><span class="lb">上榜</span>'+(r.count||0)+' 次</span>'
      + (last?'<span><span class="lb">最近</span>'+esc(last)+'</span>':'')+'</div>'
      + (r.tagline?'<div class="e-tagline">'+esc(r.tagline)+'</div>':'')
      + '</div></div>';
  });
  return h;
}
function vCat(cat){
  var list = (byCat[cat]||[]).slice().sort(function(a,b){ return (b.count||0)-(a.count||0); });
  if(!list.length) return '<div class="empty"><span class="big">404</span>未找到分类：'+esc(cat)+'</div>'+footHTML();
  var h = '<div class="shelf-h">分类书架<br><b>'+esc(cat)+'</b></div>'
    + '<div class="shelf-sub">共 '+list.length+' 个项目档案 · 按上榜次数排序 · 点击项目名进入详情</div><div class="shelf-list" id="shelflist">';
  h += catSlice(list, 0) + '</div>';
  if(list.length > CAT_LIMIT){
    h += '<button class="more-btn" id="morecat">加载更多（已显示 '+Math.min(CAT_LIMIT,list.length)+' / '+list.length+'）</button>';
    window.__moreCat = function(){
      var el = document.getElementById('shelflist');
      el.insertAdjacentHTML('beforeend', catSlice(list, el.children.length));
      var b = document.getElementById('morecat');
      if(el.children.length >= list.length){ if(b) b.remove(); }
      else if(b){ b.textContent = '加载更多（已显示 '+el.children.length+' / '+list.length+'）'; }
    };
    var btn = null;
    setTimeout(function(){ btn = document.getElementById('morecat'); if(btn) btn.setAttribute('onclick','window.__moreCat()'); },0);
  }
  return h + footHTML();
}
function vProject(repo){
  var r = PROJ[repo] || byRepo[repo];
  if(!r) return '<div class="empty"><span class="big">404</span>未找到项目：'+esc(repo)+'</div>'+footHTML();
  var recs = (r.records&&r.records.length) ? r.records : (byRepo[repo]||{records:[]}).records;
  recs = recs.slice().sort(function(a,b){ return a.date<b.date?-1:1; });
  var cnt = r.count || recs.length;
  var h = '<div class="pj-head"><div class="kicker">PROJECT FILE · 项目档案</div>'
    + '<h1><a href="'+esc(safeURL(r.url))+'" target="_blank" rel="noopener noreferrer">'+esc(r.repo)+' ↗</a></h1>'
    + '<div class="pj-meta"><span>'+langDot(r.lang)+'</span>'
    + '<span><b>'+cnt+'</b> 次上榜</span><span>★ 总星 <b>'+fmt(r.total!=null?r.total:(r.maxTotal!=null?r.maxTotal:null))+'</b></span>'
    + (r.first?'<span>首次 <b>'+esc(r.first)+'</b></span>':'')
    + (r.last?'<span>最近 <b>'+esc(r.last)+'</b></span>':'')
    + '<span style="color:var(--ink)">『'+esc(r.cat||'未分类')+'』</span></div></div>';
  if(r.tagline) h += '<div class="e-tagline" style="margin-top:22px;font-size:18px">'+esc(r.tagline)+'</div>';
  if(r.desc) h += '<div class="e-desc" style="font-size:14px;max-width:780px;line-height:2;margin-top:6px">'+esc(r.desc)+'</div>';
  h += '<div class="timeline"><h2>■ 上榜全记录 · '+recs.length+' 期'
    + (r.src==='archive'?' <span style="font-size:12px;color:var(--grey);font-family:var(--cn);font-weight:400">（来自项目档案 · 权威源）</span>':'')
    + '</h2><table class="tl-table">'
    + '<tr><th>日期 / 周期</th><th>榜单排名</th><th>榜单新增</th><th>总星</th><th>较上次同类记录</th></tr>';
  recs.forEach(function(rec,i){
    var delta = '';
    var previous=null;
    for(var index=i-1;index>=0;index--){if((recs[index].type||'daily')===(rec.type||'daily')){previous=recs[index];break;}}
    if(previous && rec.total!=null && previous.total!=null){
      var dv = rec.total - previous.total;
      delta = dv>=0 ? '<span class="dn">+'+fmt(dv)+'</span>' : '<span class="up">'+fmt(dv)+'</span>';
    }
    var target=rec.type==='weekly'?'#/week/'+rec.period:rec.type==='monthly'?'#/month/'+rec.period:'#/day/'+rec.date;
    h += '<tr onclick="go(\''+target+'\')"><td class="d">'+esc(rec.type==='weekly'?rec.period:rec.date)+'</td>'
      + '<td><b>'+esc(rec.rank_label||'#'+(rec.rank||'—'))+'</b></td><td>'+(rec.today==null?'暂未获取':'+'+fmt(rec.today))+'</td><td>'+fmt(rec.total)+'</td><td>'+delta+'</td></tr>';
  });
  return h + '</table></div>' + footHTML();
}
function vAi(dateStr){
  var f = AID[dateStr];
  if(!f) return '<div class="empty"><span class="big">404</span>当日无 AI 前沿日报：'+esc(dateStr)+'</div>'+footHTML();
  var d = null;
  ISSUES.forEach(function(x){ if(x.date===dateStr && x.type==='daily') d = x; });
  var h = '<div class="mast"><div>'
    + '<div class="kicker"><b class="p">GH WEEKLY</b> AI FRONTIER</div>'
    + '<h1><span class="d" style="color:var(--purple)">'+dateStr.replace(/-/g,'.')+'</span></h1>'
    + '<div class="brandline"><i class="p">GITHUB 每日项目推送</i>AI 前沿完整版 · '+aiCount(f)+' 条</div></div>'
    + '<div class="side-info"><div class="issue-no">AI DAILY<br><b>'+f.sections.length+'</b> 个板块</div>'
    + (d?'<div class="wd" style="cursor:pointer" onclick="go(\'#/day/'+dateStr+'\')">→ 查看同日 GitHub 日报</div>':'')+'</div></div>';
  h += '<div class="aiwrap">';
  f.sections.forEach(function(s){
    h += '<div class="sec"><h3>'+esc(s.title)+'</h3>'+aiItemsHTML(s.items)+'</div>';
  });
  h += '</div><div class="srcfile">完整原文：AI前沿资讯/日报/'+esc(f.file)+'</div>';
  return h + footHTML();
}
function vAbout(){
  var h = '<div class="shelf-h">关于本刊<br><b>ABOUT</b></div><div class="about">'
    + '<div class="quote"><b>GitHub 每日项目推送</b>将开源项目榜单、AI 前沿资讯和分类档案整理为可搜索、可离线阅读的中文杂志。</div>'
    + '<p>本页是这套系统的<b>杂志式总览刊</b>——把每期日报、AI 前沿速递、项目档案汇成一本可以翻的杂志。左侧目录按 日 / 周 / 月 / 分类 / AI 前沿 组织，底部支持全文搜索。</p>'
    + '<h3>■ 数据口径</h3><ul>'
    + '<li>报告数据：成功解析 <b>'+META.count_daily+'</b> 期日报、<b>'+META.count_weekly+'</b> 期周报、<b>'+META.count_monthly+'</b> 期月报；日报、周报与月报独立编号。数据跨度 '+(META.span[0]||'暂无')+' → '+(META.span[1]||'暂无')+'</li>'
    + '<li>期号从第 001 期开始，按已收录且成功解析的同类报告日期连续排列，与日期中的“几号”无关。早期未收录的日期不补造内容；补入更早的史料时会重新排序。</li>'
    + '<li>项目档案：<b>'+META.count_archives+'</b> 份，来自 项目分类库/ 的 owner-repo.md；项目详情页的上榜时间线以档案「历史上榜记录」表为权威源</li>'
    + '<li>AI 前沿：来自 AI前沿资讯/日报/ 的当日完整采集（<b>'+META.count_ai_days+'</b> 天），日报内精选速递为其中节选</li>'
    + '<li>补档报告：<b>'+(META.count_backfill||0)+'</b> 期，带 🗂 标识、快照时间及可获取的原始来源；星数属于快照时点。</li>'
    + '<li>项目累计次数以去重后的日榜、周榜记录统计，月报聚合不重复计次；同周期以档案记录优先。首次收录不代表项目创建时间。</li>'
    + '<li>周月新增合计仅覆盖已收录日榜，不能代表完整周期净增长；详情中的星数差是两次同类记录间的变化。</li>'
    + '<li>历史原文保留采集时的表述和来源，未经逐条重新核验；转载、传闻和过期信息以原始官方公告为准。未解析的文件不纳入统计。</li>'
    + '<li>PDF 史料：<b>'+(META.pdf_files||[]).length+'</b> 份，作为独立历史资料提供，未纳入 HTML 榜单期数及项目统计。</li>'
    + '<li>HOT 标记 = 当日新增 ⭐ ≥ 800；所有数字均来自真实抓取，抓不到写「暂未获取」，禁止编造</li>'
    + '</ul>'
    + '<h3>■ 怎么用</h3><ul>'
    + '<li>左侧边栏可整体折叠（左上角绿钮），分组可展开/收起，状态会被记住</li>'
    + '<li>本页为单文件离线 HTML，双击即可打开；每日定时任务完成后自动重建更新</li>'
    + '<li>搜索框支持项目名 / 语言 / 描述 / 分类的中英文即时搜索</li>'
    + '</ul>'
    + '<h3>■ 相关文件</h3><ul>'
    + '<li>当期日报：<a href="GitHub热点日报_'+(latest?latest.date:'')+'.html" target="_blank">GitHub热点日报_'+(latest?latest.date:'')+'.html</a></li>'
    + '<li>项目库总索引：<a href="项目分类库/_索引.md">项目分类库/_索引.md</a></li>'
    + '<li>公开版使用说明：<a href="../README.md">README.md</a></li>'
    + (META.pdf_files||[]).map(function(file){return '<li>PDF 史料：<a href="'+esc(encodeURI(file))+'" target="_blank" rel="noopener">'+esc(file)+'</a></li>';}).join('')
    + '</ul></div>';
  return h + footHTML();
}
function vSearch(qs){
  var q = (qs||'').toLowerCase();
  var hits = PKEYS.map(function(k){ return PROJ[k]; }).filter(function(r){
    return q && ((r.repo||'').toLowerCase().indexOf(q)>-1 || (r.lang||'').toLowerCase().indexOf(q)>-1
      || (r.tagline||'').toLowerCase().indexOf(q)>-1 || (r.desc||'').toLowerCase().indexOf(q)>-1
      || (r.cat||'').toLowerCase().indexOf(q)>-1);
  }).sort(function(a,b){ return (b.count||0)-(a.count||0); });
  var h = '<div class="shelf-h">搜索<br><b>“'+esc(q)+'”</b></div>'
    + '<div class="sr-count" role="status">'+hits.length+' 个项目命中</div><div class="shelf-list" id="searchlist">';
  if(!hits.length) h += '<div class="empty"><span class="big">∅</span>没有匹配的项目</div>';
  h+=catSlice(hits,0)+'</div>';
  if(hits.length>CAT_LIMIT){
    h+='<button class="more-btn" id="moresearch" onclick="window.__moreSearch()">加载更多（已显示 '+CAT_LIMIT+' / '+hits.length+'）</button>';
    window.__moreSearch=function(){
      var list=document.getElementById('searchlist'),button=document.getElementById('moresearch');
      list.insertAdjacentHTML('beforeend',catSlice(hits,list.children.length));
      if(list.children.length>=hits.length)button.remove();
      else button.textContent='加载更多（已显示 '+list.children.length+' / '+hits.length+'）';
    };
  }
  return h + footHTML();
}

/* 路由 */
window.go = function(hash){
  if(window.innerWidth<=900&&document.activeElement!==q){document.body.classList.remove('side-on');applySide();}
  location.hash = hash;
};
function enableKeyboard(root){
  root.querySelectorAll('[onclick]').forEach(function(element){
    if(!/^(A|BUTTON|INPUT)$/.test(element.tagName)){element.setAttribute('role','button');element.tabIndex=0;}
  });
}
document.addEventListener('keydown',function(event){
  var target=event.target.closest('[role="button"]');
  if(target&&(event.key==='Enter'||event.key===' ')){event.preventDefault();target.click();}
});
function route(){
  var h = location.hash || '#/';
  var m;
  view.innerHTML = (function(){
    if(h==='#/'||h==='#') return vHome();
    if((m=h.match(/^#\/day\/(\d{4}-\d{2}-\d{2})/))) return vDay(m[1]);
    if((m=h.match(/^#\/week\/([\w\-]+)/))) return vWeek(m[1]);
    if((m=h.match(/^#\/month\/(\d{4}-\d{2})/))) return vMonth(m[1]);
    if((m=h.match(/^#\/cat\/(.+)$/))) return vCat(decodePart(m[1]));
    if((m=h.match(/^#\/project\/(.+)$/))) return vProject(decodePart(m[1]));
    if((m=h.match(/^#\/ai\/(\d{4}-\d{2}-\d{2})/))) return vAi(m[1]);
    if(h==='#/about') return vAbout();
    if((m=h.match(/^#\/search\/(.*)$/))) return vSearch(decodePart(m[1]));
    return vHome();
  })();
  enableKeyboard(view);
  if(document.activeElement!==q)view.focus({preventScroll:true});
  window.scrollTo(0,0);
  markActive(h);
}
function markActive(h){
  var sel = h.replace(/[#\/]/g,'');
  document.querySelectorAll('#nav .sub,#nav .sub2').forEach(function(el){
    el.classList.remove('on');
    var oh = (el.getAttribute('onclick')||'').match(/go\('([^']+)'\)/);
    if(oh && oh[1].replace(/[#\/]/g,'')===sel){ el.classList.add('on');el.setAttribute('aria-current','page'); }
    else el.removeAttribute('aria-current');
  });
}

/* 搜索 */
var q = document.getElementById('q');
var st = null;
q.addEventListener('input', function(){
  clearTimeout(st);
  var v = q.value.trim();
  st = setTimeout(function(){ if(v.length>=1){ go('#/search/'+encodeURIComponent(v)); } }, 240);
});
q.addEventListener('keydown', function(e){ if(e.key==='Escape'){ q.value='';q.blur();go('#/'); } });

/* 侧边栏开合 */
var tog = document.getElementById('side-toggle');
function sideOff(){ try{ return localStorage.getItem('ghm-side-off')==='1'; }catch(e){ return false; } }
function applySide(){
  if(window.innerWidth<=900){
    document.body.classList.remove('side-off');
    tog.textContent = document.body.classList.contains('side-on') ? '☰' : '▸';
  }else{
    document.body.classList.toggle('side-off', sideOff());
    tog.textContent = sideOff() ? '▸' : '☰';
  }
  var expanded=window.innerWidth<=900?document.body.classList.contains('side-on'):!document.body.classList.contains('side-off');
  var side=document.getElementById('side');
  // 收起前先交还焦点，再将屏幕外目录移出键盘与辅助技术的访问范围。
  if(!expanded&&side.contains(document.activeElement))tog.focus();
  side.inert=!expanded;
  side.setAttribute('aria-hidden',String(!expanded));
  tog.setAttribute('aria-expanded',String(expanded));
}
tog.addEventListener('click', function(){
  if(window.innerWidth<=900){
    document.body.classList.toggle('side-on');
    tog.textContent = document.body.classList.contains('side-on')?'☰':'▸';
  }else{
    var off = !document.body.classList.contains('side-off');
    document.body.classList.toggle('side-off', off);
    try{ localStorage.setItem('ghm-side-off', off?'1':'0'); }catch(e){}
    tog.textContent = off ? '▸' : '☰';
  }
  applySide();
});

buildNav();
applySide();
window.addEventListener('hashchange', route);
window.addEventListener('resize', applySide);
route();
if(location.protocol==='http:' || location.protocol==='https:'){
  var applicationScript=document.createElement('script');applicationScript.src=new URL('pwa.js',window.ghDailyBase).href;document.body.appendChild(applicationScript);
}
})();
</script>
</body>
</html>
"""


def render_html(db: dict) -> str:
    payload = json.dumps(db, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return (SHELL
            .replace("__DB__", payload)
            .replace("__GEN__", db["generated_at"])
            .replace("__N_DAYS__", str(db["meta"]["count_days"]))
            .replace("__N_REPOS__", str(db["meta"]["count_repos"]))
            .replace("__N_ITEMS__", str(db["meta"]["count_projects"])))


def main():
    db, logs, skipped = build_db()
    if not db["issues"]:
        print("错误：未解析到任何报告数据", file=sys.stderr)
        sys.exit(1)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_HTML.write_text(render_html(db), encoding="utf-8")

    m = db["meta"]
    total_entries = m["count_projects"]
    miss_total = sum(d["meta"]["miss_total"] for d in db["issues"])
    miss_desc = sum(d["meta"]["miss_desc"] for d in db["issues"])
    has_wind = sum(1 for d in db["issues"] if d["wind"])
    bf_days = [d for d in db["issues"] if d["backfill"]]
    ai_band_days = sum(1 for d in db["issues"] if d["ai"])
    print("✔ 杂志构建完成")
    print(f"  期数：{m['count_days']} 期（{m['span'][0]} ~ {m['span'][1]}）"
          f"，其中补档 {len(bf_days)} 期、日报内 AI 速递 {ai_band_days} 期")
    print(f"  条目：{total_entries} 条上榜记录，{m['count_repos']} 个在榜项目；档案库 {m['count_archives']} 份；"
          f"AI 前沿日报 {m['count_ai_days']} 天")
    print(f"  解析质量：总星命中率 {(total_entries-miss_total)/total_entries*100:.1f}%（缺 {miss_total}）"
          f"，描述命中率 {(total_entries-miss_desc)/total_entries*100:.1f}%（缺 {miss_desc}），风向摘要 {has_wind}/{m['count_days']} 期")
    if bf_days:
        bf_miss = sum(d["meta"]["miss_total"] for d in bf_days)
        bf_n = sum(d["meta"]["quick_rows"] for d in bf_days)
        print(f"  补档期总星命中率：{(bf_n-bf_miss)/bf_n*100:.1f}%（{bf_n} 条中缺 {bf_miss}）")
    if skipped:
        print(f"  跳过 {len(skipped)} 个文件：")
        for s in skipped:
            print(f"    - {s}")
    print(f"  产物：{OUT_HTML}（{OUT_HTML.stat().st_size/1024/1024:.1f} MB）")
    print(f"  数据：{OUT_JSON}")


if __name__ == "__main__":
    main()
