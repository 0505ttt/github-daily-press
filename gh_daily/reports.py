"""日报、档案与月度聚合的公开格式；所有生成内容转义后写入 HTML。"""

from __future__ import annotations

import html
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from bs4 import BeautifulSoup

from .sources import number

CATEGORIES = ("A-AI机器学习", "B-开发者工具", "C-前端-Web", "D-后端-服务端", "E-基础设施-DevOps", "F-数据-数据库", "G-安全", "H-移动开发", "I-系统-底层", "J-区块链-Web3", "K-游戏-图形", "L-学习资源-其他")
AI_SECTIONS = ("大模型动态", "Agent与工程实践", "GitHub热门AI项目", "论文技术速览", "产业与观点")


def display(value: object, *, signed: bool = False) -> str:
    return ("+" if signed else "") + f"{value:,}" if isinstance(value, int) else "暂未获取"


def md(value: object) -> str:
    """模型和原描述不能注入 Markdown 链接、表格或 HTML。"""
    return re.sub(r"[\[\]<>*`|\\]", "", " ".join(str(value or "").split()))


STYLE = """
*{box-sizing:border-box}body{margin:0;background:#f6f8fa;color:#24292e;font:16px/1.7 -apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}a{color:#0969da;overflow-wrap:anywhere}nav{padding:16px 5%;background:#24292e;color:white;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}nav a{color:#fff}.badge{color:#decaff}main{max-width:1060px;margin:auto;padding:24px}header{padding:48px 28px;background:linear-gradient(130deg,#24292e,#21452f);color:white;border-radius:16px}h1{font-size:clamp(28px,5vw,52px);line-height:1.2;overflow-wrap:anywhere}.ai-band{background:linear-gradient(120deg,#f1eaff,#fff);border:1px solid #d4bfff;padding:24px;border-radius:14px;margin:24px 0}.wind,.project-card{background:#fff;border:1px solid #d0d7de;border-radius:12px;padding:24px;margin:24px 0}.project-card h2{margin-top:0}.rank{color:#2da44e}.stats{display:flex;gap:20px;flex-wrap:wrap}.tagline{background:#fff8c5;padding:12px}.category{background:#eaddff;color:#5b46b6;padding:4px 8px;display:inline-block}.hot{color:#cf222e;background:#ffe3da;padding:2px 8px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;background:white}th,td{padding:12px;text-align:left;border-bottom:1px solid #d0d7de}th{background:#24292e;color:white}tr:nth-child(even){background:#f0f6f2}:focus-visible{outline:3px solid #8250df;outline-offset:4px}footer{padding:32px 0;color:#57606a}@media(max-width:600px){main{padding:14px}.project-card,.ai-band{padding:16px}header{padding:24px 18px}th,td{padding:8px}}
"""


def render_ai_band(articles: list[dict], day: str, status: str = "") -> str:
    esc = html.escape
    items = "".join(f'<li>⚡ <strong>{esc(item["title"])}</strong> — {esc(item["summary"])} <a href="{esc(item["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{esc(item.get("source", "来源"))}</a></li>' for item in articles[:10])
    note = f"已核验精选 {min(len(articles), 10)} 条。" if articles else (status or "当日 AI 日报暂未生成，未使用过期内容补足。")
    return f'<section class="ai-band"><h2>⚡ AI 前沿速递</h2><p>{esc(note)}</p><ul>{items}</ul><p>完整版：AI前沿资讯/日报/{esc(day)}-AI日报.md</p></section>'


def render_report(snapshot: dict, day: str, articles: list[dict] | None = None, ai_status: str = "") -> str:
    esc = html.escape
    weekly = snapshot["period"] == "weekly"
    projects = snapshot["projects"]
    title = f"GitHub {'本周热点 Top 15' if weekly else '热点日报 Top 10'} · {day}"
    cards, rows = [], []
    growth_title = "本周新增" if weekly else "今日新增"
    for project in projects:
        repo, url = esc(project["repo"]), esc(project["url"], quote=True)
        growth = display(project["growth"], signed=True)
        hot = ' class="hot"' if project["growth"] is not None and project["growth"] >= 800 else ""
        description = project.get("editorial") or ("仓库原描述：" + project["description"] if project["description"] else "项目介绍暂未获取。")
        cards.append(f'<article class="project-card"><h2><span class="rank">#{project["rank"]}</span> <a href="{url}" target="_blank" rel="noopener noreferrer">{repo}</a></h2><div class="stats"><span>⭐ 总计 {display(project["total"])} Stars</span><span{hot}>{growth_title} {growth}</span><span>{esc(project["lang"])}</span></div><p class="tagline">{esc(project.get("tagline") or project["description"] or "项目说明暂未获取")}</p><p class="description">{esc(description)}</p><p><strong>适用领域</strong>：{esc(project.get("usage") or "暂无更多背景资料")}</p><span class="category">{esc(project["category"])}</span></article>')
        rows.append(f'<tr><td>#{project["rank"]}</td><td><a href="{url}">{repo}</a></td><td>{esc(project["lang"])}</td><td>{growth}</td><td>{esc(project["category"])}</td></tr>')
    languages = Counter(project["lang"] for project in projects)
    wind = f"本次从 GitHub Trending 实际获取 {len(projects)} 个项目。" + "、".join(f"{language} {count} 个" for language, count in languages.most_common(4)) + "。项目用途以仓库 README 与顶部描述为依据，缺失数字不参与统计。"
    editorial_status = "success" if all(project.get("editorial") for project in projects) else "pending"
    return f'<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="editorial-status" content="{editorial_status}"><title>{esc(title)}</title><style>{STYLE}</style></head><body><nav><a href="GitHub热点杂志.html">GitHub 每日项目推送</a><span class="badge">融合版 · AI 前沿 × 开源热点</span></nav><main><header><p>开源热点 · 真实来源</p><h1>{esc(title)}</h1><p>每一天，追踪开源世界的脉搏</p><p>数据采集时间：{esc(snapshot["fetched_at"])}；<a href="{esc(snapshot["source"], quote=True)}" style="color:#a5e8bb">原始榜单</a></p></header>{render_ai_band(articles or [], day, ai_status)}<section class="wind"><h2>{"本周" if weekly else "今日"}风向</h2><p>{esc(wind)}</p></section>{"".join(cards)}<h2>速览表</h2><div class="table-wrap"><table><thead><tr><th>排名</th><th>项目</th><th>语言</th><th>{growth_title}</th><th>知识分类</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div><footer>数字为采集时点的真实值；暂无数据时显示“暂未获取”。模型归纳仅用于解释已采集的资料。</footer></main></body></html>'


def replace_ai_band(text: str, articles: list[dict], day: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    old = soup.select_one(".ai-band")
    if old is None:
        raise ValueError("现有日报缺少 AI 板块，未自动重写历史版式")
    old.replace_with(BeautifulSoup(render_ai_band(articles, day), "html.parser"))
    return str(soup)


def render_ai_markdown(day: str, articles: list[dict], sources: list[dict]) -> str:
    lines = [f"# AI前沿日报 {day}", "", "采集窗口：生成时点前 48 小时。仅收录可验证发布日期与来源的内容。", ""]
    for index, section in enumerate(AI_SECTIONS, 1):
        lines.extend([f"## {'一二三四五'[index - 1]}、{section}", ""])
        subset = [item for item in articles if item["section"] == section]
        for item in subset:
            lines.extend([f"- **{md(item['title'])}** — {md(item['summary'])} [来源]({item['url']})", f"  发布：{item['published_at']}；采集来源：{md(item['source'])}；来源编号：{item['source_id']}", ""])
        if not subset:
            lines.extend(["本窗口暂无符合要求的已核验内容。", ""])
    lines.extend([f"今日总结：本次收录 {len(articles)} 条有日期与来源的资讯，未以旧消息补足数量。", "", "## 今日采集情况", ""])
    labels = {"success": "成功", "empty": "暂无新内容", "failed": "失败", "unavailable": "未配置"}
    for source in sources:
        lines.append(f"- {md(source['source'])}：{labels.get(source['status'], '未完成')}；{md(source.get('reason') or ('近48小时采集 ' + str(source.get('count', 0)) + ' 条'))}。")
    return "\n".join(lines) + "\n"


def read_ai_markdown(path: Path) -> list[dict]:
    soup_items = []
    section = AI_SECTIONS[0]
    for line in path.read_text(encoding="utf-8").splitlines():
        for candidate in AI_SECTIONS:
            if line.startswith("## ") and candidate in line:
                section = candidate
        match = re.search(r"\*\*(.+?)\*\*\s*[—-]\s*(.*?)\s*\[(?:来源|[^\]]+)\]\((https?://[^\s)]+)\)", line)
        if match:
            soup_items.append({"title": match.group(1), "summary": match.group(2), "url": match.group(3), "section": section, "source": "原始来源"})
    return soup_items


def archive_records(text: str) -> list[dict]:
    records = []
    for line in text.splitlines():
        parts = [item.strip() for item in line.strip().strip("|").split("|")]
        if len(parts) >= 4 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[0]) and re.fullmatch(r"W?#?\d+", parts[1]):
            records.append({"date": parts[0], "rank": parts[1], "weekly": parts[1].startswith("W"), "total": number(parts[2]), "growth": number(parts[3])})
    return records


def archive_text(project: dict, day: str, weekly: bool, previous: str = "", *, replace_record: bool = False) -> tuple[str, bool]:
    rank = f"{'W' if weekly else ''}#{project['rank']}"
    records = archive_records(previous)
    explanation_changed = False
    if previous and "<!-- 项目介绍待补齐 -->" in previous and project.get("editorial"):
        previous = previous.replace("<!-- 项目介绍待补齐 -->\n", "")
        for heading, value in (("知识归类", project["category"]), ("详细介绍", project["editorial"]), ("适用领域", project["usage"])):
            previous = re.sub(r"(## " + heading + r"\n).*?(?=\n## |\Z)", lambda match: match.group(1) + md(value) + "\n", previous, flags=re.S)
        explanation_changed = True
    if any(row["date"] == day and row["weekly"] == weekly for row in records):
        if replace_record:
            before = previous
            rank_pattern = r"W#?\d+" if weekly else r"#?\d+"
            previous = re.sub(r"(?m)^\|\s*" + re.escape(day) + r"\s*\|\s*" + rank_pattern + r"\s*\|[^\n]*$", lambda _: f"| {day} | {rank} | {display(project['total'])} | {display(project['growth'], signed=True)} |", previous)
            if day == max(row["date"] for row in records):
                previous = re.sub(r"(?m)^-\s*\*\*Star\*\*[：:].*$", lambda _: f"- **Star**：总计 {display(project['total'])} | {'本周新增' if weekly else '今日新增'} {display(project['growth'], signed=True)}", previous)
            explanation_changed |= before != previous
        return previous, explanation_changed
    if not previous:
        pending = "" if project.get("editorial") else "<!-- 项目介绍待补齐 -->\n"
        previous = f"# {project['repo']}\n\n> {md(project.get('tagline') or project['description'] or '项目说明暂未获取')}\n\n{pending}## 基本信息\n- **仓库链接**：{project['url']}\n- **主语言**：{md(project['lang'])}\n- **Star**：总计 {display(project['total'])} | {'本周新增' if weekly else '今日新增'} {display(project['growth'], signed=True)}\n- **首次上榜**：{day}\n- **最近上榜**：{day}\n- **累计上榜**：0 次\n\n## 知识归类\n{md(project['category'])}\n\n## 详细介绍\n{md(project.get('editorial') or project['description'] or '暂未获取')}\n\n## 适用领域\n{md(project.get('usage') or '暂无更多背景资料')}\n\n## 背景调研\n暂无更多背景资料。\n\n## 历史上榜记录\n| 日期 | 当日排名 | Star 总计 | 今日新增 |\n|------|---------|----------|---------|\n"
    added = {"date": day, "rank": rank, "weekly": weekly, "total": project["total"], "growth": project["growth"]}
    records.append(added)
    # 表内可识别记录是计数权威；日榜与周榜同日分别记一次。
    recent = max(row["date"] for row in records)
    previous = re.sub(r"(?m)^-\s*\*\*最近上榜\*\*[：:].*$", f"- **最近上榜**：{recent}", previous)
    previous = re.sub(r"(?m)^-\s*\*\*累计上榜\*\*[：:].*$", f"- **累计上榜**：{len(records)} 次", previous)
    if day == recent:
        previous = re.sub(r"(?m)^-\s*\*\*Star\*\*[：:].*$", f"- **Star**：总计 {display(project['total'])} | {'本周新增' if weekly else '今日新增'} {display(project['growth'], signed=True)}", previous)
    previous = previous.rstrip() + f"\n| {day} | {rank} | {display(project['total'])} | {display(project['growth'], signed=True)} |\n"
    return previous, True


def index_text(root: Path) -> str:
    base = root / "GitHub项目分析" / "项目分类库"
    rows, categories = [], Counter()
    for path in sorted(base.rglob("*.md")):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^#\s+([\w.-]+/[\w.-]+)\s*$", text, re.M)
        if not match:
            continue
        records = archive_records(text)
        category_match = re.search(r"##\s*知识归类\s*\n+([^\n]+)", text)
        category = category_match.group(1).strip() if category_match else (path.relative_to(base).parts[0] if len(path.relative_to(base).parts) > 1 else "未分类")
        categories[category] += 1
        dates = sorted(row["date"] for row in records)
        rows.append(f"| {match.group(1)} | {category} | {dates[0] if dates else '暂未获取'} | {dates[-1] if dates else '暂未获取'} | {len(records)} | [{path.stem}]({path.relative_to(base).as_posix()}) |")
    lines = ["# GitHub 项目分类库索引", "", f"共 {len(rows)} 个项目。上榜次数按可解析的真实历史记录统计，日榜与周榜分别计数。", "", "## 按分类统计", "", "| 分类 | 项目数 |", "|---|---:|"]
    lines.extend(f"| {category} | {count} |" for category, count in sorted(categories.items()))
    lines.extend(["", "## 项目总索引", "", "| 项目名 | 分类 | 首次出现 | 最近出现 | 上榜次数 | 文件位置 |", "|---|---|---|---|---:|---|"])
    return "\n".join(lines + rows) + "\n"


def aggregate_month(root: Path, month: str) -> dict:
    """日榜为次数锚点，档案日记录补总星；周榜不重复累加。"""
    projects, dates, records = {}, [], {}
    base = root / "GitHub项目分析"
    for path in sorted((base / "项目分类库").rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^#\s+([\w.-]+/[\w.-]+)\s*$", text, re.M)
        if match:
            records[match.group(1)] = {row["date"]: row for row in archive_records(text) if not row["weekly"] and row["date"].startswith(month)}
    for path in sorted(base.glob(f"GitHub热点日报_{month}-??.html")):
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        tables = soup.find_all("table")
        if not tables:
            continue
        day = path.stem.rsplit("_", 1)[-1]
        seen = set()
        for row in tables[-1].find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 5:
                continue
            repo = cells[1].get_text(" ", strip=True)
            if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo) or repo in seen:
                continue
            seen.add(repo)
            project = projects.setdefault(repo, {"repo": repo, "category": cells[4].get_text(" ", strip=True), "days": set(), "totals": {}})
            project["days"].add(day)
            record = records.get(repo, {}).get(day)
            if record and record["total"] is not None:
                project["totals"][day] = record["total"]
            else:
                for card in soup.select(".project-card"):
                    link = card.find("a", href=True)
                    if link and link["href"].rstrip("/") == f"https://github.com/{repo}":
                        total = re.search(r"总计\s*([\d,]+)", card.get_text(" ", strip=True))
                        if total:
                            project["totals"][day] = number(total.group(1))
                        break
        if seen:
            dates.append(day)
    category_counts = Counter()
    new_projects = []
    for project in projects.values():
        category_counts[project["category"]] += 1
        totals = sorted(project["totals"].items())
        project["growth"] = totals[-1][1] - totals[0][1] if len(totals) >= 2 else None
        project["growth_start"] = totals[0][0] if totals else ""
        project["growth_end"] = totals[-1][0] if totals else ""
        project["count"] = len(project["days"])
    for path in (base / "项目分类库").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"首次上榜\*?\*?[：:]\s*(\d{4}-\d{2}-\d{2})", text)
        repo_match = re.search(r"^#\s+([\w.-]+/[\w.-]+)\s*$", text, re.M)
        if match and repo_match and match.group(1).startswith(month):
            new_projects.append(repo_match.group(1))
    return {"month": month, "days": dates, "projects": list(projects.values()), "categories": category_counts, "new_projects": sorted(set(new_projects))}


def render_month(data: dict) -> str:
    esc = html.escape
    month = data["month"]
    by_count = sorted(data["projects"], key=lambda row: (-row["count"], row["repo"]))
    by_growth = sorted((row for row in data["projects"] if row["growth"] is not None), key=lambda row: (-row["growth"], row["repo"]))
    count_rows = "".join(f'<tr><td>{i}</td><td><a href="https://github.com/{esc(row["repo"])}">{esc(row["repo"])}</a></td><td>{row["count"]}</td></tr>' for i, row in enumerate(by_count, 1))
    growth_rows = "".join(f'<tr><td>{esc(row["repo"])}</td><td>{row["growth"]:+,}</td><td>{row["growth_start"]} 至 {row["growth_end"]}</td></tr>' for row in by_growth)
    category_rows = "".join(f'<tr><td>{esc(category)}</td><td>{count}</td></tr>' for category, count in data["categories"].most_common())
    new_items = "".join(f'<li><a href="https://github.com/{esc(repo)}">{esc(repo)}</a></li>' for repo in data["new_projects"])
    # 末表保持五列，是杂志解析器使用的速览锚点。
    quick = "".join(f'<tr><td>#{i}</td><td><a href="https://github.com/{esc(row["repo"])}">{esc(row["repo"])}</a></td><td>暂未获取</td><td>暂未获取</td><td>{esc(row["category"])}</td></tr>' for i, row in enumerate(by_count[:15], 1))
    return f'<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GitHub 热点月报 {month}</title><style>{STYLE}</style></head><body><nav><a href="GitHub热点杂志.html">GitHub 每日项目推送</a></nav><main><header><h1>GitHub 热点月报 {month}</h1><p>每月追踪开源世界脉搏</p></header><section class="wind"><h2>本月概览</h2><p>读取本地真实日报 {len(data["days"])} 期，覆盖 {len(data["projects"])} 个项目。缺失日期未补造；周榜不计入日榜次数。星数变化是月内最早与最晚可用观测之差，不代表完整自然月增长。</p></section><h2>上榜次数榜</h2><div class="table-wrap"><table><tr><th>排名</th><th>项目</th><th>上榜天数</th></tr>{count_rows}</table></div><h2>Star 观测变化榜</h2><div class="table-wrap"><table><tr><th>项目</th><th>变化</th><th>观测区间</th></tr>{growth_rows}</table></div><h2>分类分布</h2><table><tr><th>分类</th><th>去重项目数</th></tr>{category_rows}</table><h2>当月新入库项目</h2><ul>{new_items}</ul><h2>速览表</h2><div class="table-wrap"><table><tr><th>排名</th><th>项目</th><th>语言</th><th>当日新增</th><th>分类</th></tr>{quick}</table></div></main></body></html>'
