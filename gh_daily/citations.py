"""引用的确定性检查；通过检查不等于新闻已获独立事实认证。"""
from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

POLICY_START = "2026-10-26"


def require_article_url(url: str) -> None:
    """首页、栏目、RSS 和搜索入口只能用于发现资料，不能充当文章。"""
    parsed = urlsplit(url)
    path = unquote(parsed.path).rstrip("/").lower()
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.port not in {None, 443} or "\\" in url or any(ord(c) < 32 for c in url)):
        raise ValueError("事实引用必须是无凭据的 HTTPS 原文地址")
    if (not path or path in {"/news", "/blog", "/press", "/research", "/search", "/feed", "/rss"}
            or re.search(r"/(?:feed|rss)(?:\.xml)?$|/search(?:/|$)", path)
            or path.endswith((".rss", "/rss.xml"))
            or path.startswith(("/category/", "/tag/", "/topics/"))):
        raise ValueError("引用指向首页、栏目、搜索或订阅入口，请替换为具体原文")


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def validate_claim(item: dict, source: dict) -> None:
    require_article_url(source["url"])
    evidence = item.get("evidence")
    if (not isinstance(evidence, list) or not 1 <= len(evidence) <= 3
            or any(not isinstance(quote, str) or not 8 <= len(quote.strip()) <= 600 for quote in evidence)):
        raise ValueError("每条归纳必须提供一至三段原文证据")
    original = _normalized(source.get("text", ""))
    if any(_normalized(quote) not in original for quote in evidence):
        raise ValueError("引用证据不是已读取原文中的连续片段")
    quoted = _normalized(" ".join(evidence))
    claim = _normalized(item["title"] + " " + item["summary"])
    # 不自动换算金额、百分比或相对差距；证据不足时让编辑删去精确数字。
    def numbers(text: str) -> set[str]:
        return set(re.findall(r"\d+(?:[.,]\d+)*", text))
    if numbers(claim) - numbers(quoted):
        raise ValueError("归纳含原文证据未直接支持的数字，请删除或补充证据")
    # 拦截把模型名、机构名或测试名挂到无关文章的常见情况。
    entities = set(re.findall(r"[A-Za-z][A-Za-z0-9_.-]{2,}", claim))
    stopwords = {"the", "and", "for", "with", "agent", "agents", "ai", "llm"}
    for entity in entities:
        if entity.lower() not in stopwords and entity.casefold() not in quoted.casefold():
            raise ValueError("归纳中的模型、机构或技术名称未出现在所引证据中")


def check_text(text: str, *, html: bool = False) -> list[str]:
    """只检查新闻条目引用；导航、完整版路径等不属于事实引用。"""
    if html:
        soup = BeautifulSoup(text, "html.parser")
        links = []
        for band in soup.select(".ai-band, .ai-week"):
            for item in band.select("li"):
                links.extend([a.get("href", "") for a in item.select("a[href]")] or [""])
    else:
        links = []
        for line in text.splitlines():
            if re.match(r"\s*-\s+\*\*", line):
                found = re.findall(r"\[[^\]]+\]\((https?://[^\s)]+)\)", line)
                if not found:
                    links.append("")
                links.extend(found)
    errors = []
    for link in links:
        try:
            require_article_url(link)
        except ValueError as error:
            errors.append(str(error))
    return errors


def check_workspace(root: Path, *, since: str = POLICY_START) -> list[str]:
    errors = []
    for path in sorted((root / "AI前沿资讯/日报").glob("????-??-??-AI日报.md")):
        if path.name[:10] >= since:
            errors.extend(f"{path.relative_to(root)}：{error}" for error in check_text(path.read_text(encoding="utf-8")))
    for path in sorted((root / "GitHub项目分析").glob("*.html")):
        daily = re.fullmatch(r"GitHub热点日报_(\d{4}-\d{2}-\d{2})\.html", path.name)
        if daily and daily[1] >= since:
            errors.extend(f"{path.relative_to(root)}：{error}" for error in check_text(path.read_text(encoding="utf-8"), html=True))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 AI 日报及融合速递的原文链接格式")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--since", default=POLICY_START)
    args = parser.parse_args()
    errors = check_workspace(args.root, since=args.since)
    for error in errors:
        print(error)
    print("引用入口检查未通过。" if errors else "引用入口检查通过；原文可达性、日期和语义仍需联网核验。")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
