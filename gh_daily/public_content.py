"""公开资料中的采编注记处理；不使用部署者的姓名或私人任务名称。"""
from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup, Comment, NavigableString


# 这些规则识别报告自身的运行注记，不按新闻中出现的工具名过滤内容。
NOTE_RULES = (
    (re.compile(r"与当日\s*\d{1,2}:\d{2}\s*(?:原)?(?:定时|自动|采编)任务的榜单(?:一致(?:或相近)?|相近)"),
     "仅反映该快照时点的榜单，不代表整日完整榜单"),
    (re.compile(r"原日报因(?:任务|定时任务)[^，。\n<>]{0,40}未生成"),
     "历史日报记录未收录"),
    (re.compile(r"[^。！？\n<>]{0,80}(?:正是|也正是)驱动[「“](?:本刊|本报告|[^」”\n]{0,40}(?:日报|周报|月报))[」”]的[^。！？\n<>]{1,80}[。]?"),
     ""),
    (re.compile(r"(?:本报告|本日报|本刊)(?:由[^。\n<>·|]{1,80}(?:自动(?:采集|抓取)?(?:生成|整理)|精心整理))"),
     "本报告依据公开资料整理"),
)
ATTRIBUTION = re.compile(r"(?P<prefix>(?:^|[·|\n>])\s*)(?:由\s*)?[「“][^」”\n]{1,80}[」”](?:(?:每日|每周|每月|定时|自动|私人|采编|情报|融合|发布|同步|执行)){0,8}任务(?:生成)?(?:（[^）\n]{0,60}）)?")
TOOL_BYLINE = re.compile(r"由\s*[^·|。\n<>]{1,80}?\s*自动(?:采集|抓取)?(?:生成|整理)")
PRIVATE_NOTE_LABEL = re.compile(r"^(?:私人|内部|本机)?(?:运行备注|执行备注|任务备注|调度备注)\s*[：:]")
PRIVATE_NOTE_MARKER = re.compile(r"(?:私人|内部|本机)?(?:运行备注|执行备注|任务备注|调度备注)\s*[：:]")
EDITORIAL_BLOCKS = "footer, .footer, .footer-note, .foot, .foot-note, .table-end, .meta"
NARRATIVE_FIELDS = {"note", "backfill_note", "description", "desc", "summary", "intro", "tagline", "wind", "body", "content", "t", "d"}


class EditorialContentError(ValueError):
    """含无法可靠界定范围的私人运行注记，拒绝导入且不回显正文。"""


def sanitize_structured_content(value, *, field: str = ""):
    """只清理叙述字段的明确注记；日期、快照、链接和身份字段原样保留。"""
    if isinstance(value, str):
        return neutralize_notes(value) if field in NARRATIVE_FIELDS else value
    if isinstance(value, list):
        return [sanitize_structured_content(item, field=field) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_structured_content(item, field=key) for key, item in value.items()}
    return value


def sanitize_embedded_content(text: str) -> str:
    """定点更新杂志 JSON，避免文本正则跨越 JSON 字符串破坏数据或脚本。"""
    block = re.search(r"<script\b(?=[^>]*\bid\s*=\s*['\"]DB['\"])[^>]*>(?P<data>[\s\S]*?)</script\s*>", text, re.I)
    try:
        if block is not None:
            start, end = block.span("data")
            data = json.loads(text[start:end])
        else:
            match = re.search(r"\b(?:const|let|var)\s+DB\s*=\s*", text)
            if match is None:
                raise EditorialContentError("总览内嵌数据结构未识别，未修改该历史文件。")
            start = match.end()
            data, length = json.JSONDecoder().raw_decode(text[start:])
            end = start + length
    except (json.JSONDecodeError, ValueError):
        raise EditorialContentError("总览内嵌数据无法解析，未修改该历史文件。") from None
    clean = sanitize_structured_content(data)
    encoded = text[start:end] if clean == data else json.dumps(clean, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return neutralize_notes(text[:start]) + encoded + neutralize_notes(text[end:])


def neutralize_notes(text: str, *, attribution: bool = False) -> str:
    """保持新闻事实与来源，仅中性化报告自身的采编注记。"""
    for pattern, replacement in NOTE_RULES:
        text = pattern.sub(replacement, text)
    if attribution:
        text = ATTRIBUTION.sub(lambda match: match.group("prefix") + "公开资料整理", text)
        text = TOOL_BYLINE.sub("依据公开资料整理", text)
        if "快照" not in text:
            text = re.sub(r"(\d{4}-\d{2}-\d{2})\s+\d{1,2}:\d{2}(?:\s*\(?CST\)?)?", r"\1", text)
            text = re.sub(r"采集时间\s*\d{1,2}:\d{2}(?:\s*CST)?", "数据以当日采集为准", text)
            text = text.replace("当日二次刷新，数据为最新", "数据对应当次采集时点")
    return text


def sanitize_editorial_content(text: str, *, html: bool) -> str:
    if not html:
        if PRIVATE_NOTE_MARKER.search(text):
            raise EditorialContentError("资料含私人运行注记，请先整理公开正文；本次未导入。")
        lines = []
        for line in text.splitlines(keepends=True):
            plain = line.lstrip(" >*_-\t")
            byline = bool(re.match(r"(?:本报告|本日报|本刊)", plain))
            lines.append(neutralize_notes(line, attribution=byline))
        return "".join(lines)

    soup = BeautifulSoup(text, "html.parser")
    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()
    for metadata in soup.find_all("meta"):
        if str(metadata.get("name", "")).lower() in {"author", "generator"}:
            metadata.decompose()
    # 标签可能被强调标记或换行拆开。不能只删标签而留下私人正文。
    if PRIVATE_NOTE_MARKER.search(soup.get_text("", strip=False)):
        raise EditorialContentError("资料含私人运行注记，请先整理公开正文；本次未导入。")
    # 页脚是采编说明，不是新闻正文。先在其完整文本上处理，兼容被标签拆开的署名。
    for block in list(soup.select(EDITORIAL_BLOCKS)):
        if block.parent is None:
            continue
        plain = block.get_text(" ", strip=True)
        clean = neutralize_notes(plain, attribution=True)
        if clean != plain:
            # 源链接即使只有“来源”二字，也以实际 URL 保留下来。
            links = [str(link.get("href")) for link in block.find_all("a", href=True)]
            block.clear()
            block.append(clean)
            for url in dict.fromkeys(links):
                if url not in clean:
                    block.append(" · ")
                    anchor = soup.new_tag("a", href=url)
                    anchor.string = "来源"
                    block.append(anchor)
    for node in list(soup.find_all(string=True)):
        if not isinstance(node, NavigableString) or node.parent.name in {"script", "style"}:
            continue
        plain = str(node)
        clean = neutralize_notes(plain, attribution=bool(re.match(r"\s*(?:数据)?(?:抓取|采集)时间", plain)))
        if clean != plain:
            node.replace_with(clean)
    return str(soup)


def contains_editorial_trace(text: str, *, html: bool = False) -> bool:
    """用于公开数据检查；教程和源码不调用此规则，避免误伤一般工具说明。"""
    if neutralize_notes(text) != text:
        return True
    if html:
        soup = BeautifulSoup(text, "html.parser")
        if PRIVATE_NOTE_MARKER.search(soup.get_text("", strip=False)):
            return True
        for footer in soup.select(EDITORIAL_BLOCKS):
            plain = footer.get_text(" ", strip=True)
            if neutralize_notes(plain, attribution=True) != plain:
                return True
        plain = soup.get_text(" ")
    else:
        plain = text
    if neutralize_notes(plain) != plain:
        return True
    if ATTRIBUTION.search(plain):
        return True
    return bool(PRIVATE_NOTE_MARKER.search(plain))
