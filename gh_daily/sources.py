"""公开来源采集：保留日期证据，不把缺失值改写成事实。"""

from __future__ import annotations

import email.utils
import hashlib
import html
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urljoin, urlparse

from bs4 import BeautifulSoup

from tools.parse_trending import parse_trending
from .tls import verified_context
from .citations import require_article_url

MAX_BODY = 4 * 1024 * 1024
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
HEADERS = {"User-Agent": "GitHubDaily/1.0 (+https://github.com)", "Accept": "application/json, text/html, application/xml;q=0.9"}


class SourceError(RuntimeError):
    """只携带可公开的错误，绝不包含响应正文、密钥或代理设置。"""


class _PinnedHTTPS(http.client.HTTPSConnection):
    """连接已校验的公网 IP，同时保留原始主机名做 TLS 和 Host 校验。"""

    def __init__(self, host: str, address: str, timeout: float):
        super().__init__(host, port=443, timeout=timeout, context=verified_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


def _public_address(host: str) -> str:
    answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    addresses = list(dict.fromkeys(answer[4][0] for answer in answers))
    if not addresses:
        raise SourceError("公开来源主机无法解析")
    for address in addresses:
        parsed = ipaddress.ip_address(address)
        if not parsed.is_global or parsed.is_multicast or parsed.is_reserved:
            raise SourceError("公开来源不允许访问私网、回环或保留地址")
    return addresses[0]


def _download_once(url: str, *, deadline: float, max_bytes: int) -> str:
    try:
        parsed = urlparse(url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.port not in {None, 443}
                or parsed.username or parsed.password or "\\" in url or len(url) > 4096
                or any(ord(char) < 32 for char in url)):
            raise SourceError("公开来源仅支持无凭据的 HTTPS 公网地址")
        address = _public_address(parsed.hostname)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SourceError("采集已超时")
        connection = _PinnedHTTPS(parsed.hostname, address, min(10, remaining))
    except (OSError, ValueError):
        raise SourceError("公开来源地址无法校验") from None
    try:
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        connection.request("GET", path, headers=HEADERS)
        response = connection.getresponse()
        # 不跟随任何重定向，官方域开放跳转也不能绕过原始来源校验。
        if 300 <= response.status < 400:
            raise SourceError("公开来源返回重定向，已停止采集")
        if not 200 <= response.status < 300:
            raise SourceError("公开来源返回失败状态")
        content_length = response.getheader("Content-Length")
        if content_length and int(content_length) > max_bytes:
            raise SourceError("来源内容超过大小限制")
        body = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SourceError("采集已超时")
            if connection.sock is not None:
                connection.sock.settimeout(min(10, remaining))
            chunk = response.read1(min(65536, max_bytes + 1 - len(body)))
            if not chunk:
                break
            body.extend(chunk)
            if len(body) > max_bytes:
                raise SourceError("来源内容超过大小限制")
        if time.monotonic() >= deadline:
            raise SourceError("采集已超时")
        return body.decode("utf-8", errors="replace")
    except (OSError, ssl.SSLError, http.client.HTTPException, ValueError):
        raise SourceError("公开来源连接失败或响应不完整") from None
    finally:
        connection.close()


def fetch(url: str, *, deadline: float | None = None, max_bytes: int = MAX_BODY) -> str:
    """每个地址至多两次；流式读取限制响应体和整体时间。"""
    limit = min(deadline or (time.monotonic() + 30), time.monotonic() + 30)
    for _ in range(2):
        remaining = limit - time.monotonic()
        if remaining <= 0:
            raise SourceError("采集已超时")
        try:
            return _download_once(url, deadline=limit, max_bytes=max_bytes)
        except SourceError:
            continue
    raise SourceError("来源无法访问或响应不完整")


def number(value: object) -> int | None:
    """只解析明确整数，1.2k 等近似值不冒充精确总星。"""
    text = str(value).strip().replace(",", "")
    match = re.fullmatch(r"\+?(\d+)(?:\s+stars?\s+(?:today|this week))?", text)
    return int(match.group(1)) if match else None


def collect_trending(period: str = "daily", *, deadline: float | None = None) -> dict:
    if period not in {"daily", "weekly"}:
        raise ValueError("榜单周期无效")
    url = f"https://github.com/trending?since={period}"
    rows = parse_trending(fetch(url, deadline=deadline), 10 if period == "daily" else 15)
    if not rows:
        raise SourceError("GitHub Trending 未解析到有效项目")
    result, seen = [], set()
    for row in rows:
        repo = row["name"]
        if not REPO.fullmatch(repo) or repo.casefold() in seen:
            continue
        seen.add(repo.casefold())
        result.append({"repo": repo, "url": f"https://github.com/{repo}", "rank": row["rank"],
                       "description": row.get("desc", ""), "lang": row.get("lang") or "未标注",
                       "total": number(row.get("total_stars")), "growth": number(row.get("today_stars")),
                       "category": "L-学习资源-其他", "usage": "暂无更多背景资料", "readme": ""})
    if not result:
        raise SourceError("GitHub Trending 仓库地址校验未通过")
    return {"source": url, "fetched_at": datetime.now(timezone.utc).isoformat(), "period": period, "projects": result}


def enrich_projects(snapshot: dict, *, deadline: float | None = None) -> list[dict]:
    """仓库元信息与 README 是项目说明的依据；失败时保留 Trending 原描述。"""
    statuses = []
    for project in snapshot["projects"]:
        repo = project["repo"]
        if deadline is not None and time.monotonic() >= deadline:
            statuses.append({"source": repo, "status": "failed", "reason": "详情采集达到时限"})
            continue
        try:
            info = json.loads(fetch(f"https://api.github.com/repos/{repo}", deadline=deadline))
            if info.get("full_name", "").casefold() != repo.casefold() or info.get("message"):
                raise SourceError("仓库元信息无法确认")
            project["description"] = info.get("description") or project["description"]
            project["lang"] = info.get("language") or project["lang"]
            project["topics"] = info.get("topics") or []
            if project["total"] is None and isinstance(info.get("stargazers_count"), int):
                project["total"] = info["stargazers_count"]
            statuses.append({"source": repo, "status": "success"})
        except (SourceError, json.JSONDecodeError, AttributeError):
            statuses.append({"source": repo, "status": "partial", "reason": "仓库详情未获取，沿用榜单原描述"})
        # README 单独限时，不能因补充背景阻塞主报告。
        try:
            readme = json.loads(fetch(f"https://api.github.com/repos/{repo}/readme", deadline=deadline, max_bytes=512000))
            import base64
            if readme.get("encoding") == "base64" and isinstance(readme.get("content"), str):
                project["readme"] = base64.b64decode(readme["content"]).decode("utf-8", errors="replace")[:5000]
        except (SourceError, json.JSONDecodeError, ValueError, AttributeError):
            pass
    return statuses


def parsed_date(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            result = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            return None
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def valid_url(value: object, base: str = "") -> str:
    if not isinstance(value, str):
        return ""
    url = urljoin(base, value)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return ""
    return url


def _text(value: object) -> str:
    raw = str(value or "")
    if "<" not in raw:
        return " ".join(html.unescape(raw).split())[:7000]
    soup = BeautifulSoup(raw, "html.parser")
    for element in soup(["script", "style"]):
        element.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())[:7000]


def parse_feed(body: str, base: str) -> list[dict]:
    root = ET.fromstring(body)
    items = []
    for node in root.iter():
        if node.tag.split("}")[-1] not in {"item", "entry"}:
            continue
        fields = {}
        links = []
        for child in node:
            key = child.tag.split("}")[-1]
            fields[key] = "".join(child.itertext())
            if key == "link":
                link = child.attrib.get("href") or (child.text or "")
                if child.attrib.get("rel", "alternate") == "alternate":
                    links.append(link)
        items.append({"title": _text(fields.get("title")), "url": valid_url(links[0], base) if links else "",
                      "published_at": fields.get("pubDate") or fields.get("published") or fields.get("updated"),
                      "text": _text(fields.get("description") or fields.get("summary") or fields.get("encoded") or fields.get("content"))})
    return items


def parse_announcements(body: str, base: str) -> list[dict]:
    """只接受页面上可验证的发布日期；不能从无日期链接推断新发布。"""
    soup = BeautifulSoup(body, "html.parser")
    items = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        queue = list(data) if isinstance(data, list) else [data]
        while queue:
            obj = queue.pop()
            if not isinstance(obj, dict):
                continue
            for key in ("@graph", "itemListElement"):
                if isinstance(obj.get(key), list):
                    queue.extend(obj[key])
            if isinstance(obj.get("item"), dict):
                queue.append(obj["item"])
            if obj.get("datePublished") and (obj.get("headline") or obj.get("name")):
                items.append({"title": _text(obj.get("headline") or obj.get("name")), "url": valid_url(obj.get("url"), base),
                              "published_at": obj["datePublished"], "text": _text(obj.get("description") or obj.get("articleBody"))})
    for stamp in soup.find_all("time"):
        container = stamp.find_parent(["article", "li"]) or stamp.parent
        link = container.find("a", href=True) if container else None
        if link:
            items.append({"title": link.get_text(" ", strip=True), "url": valid_url(link["href"], base),
                          "published_at": stamp.get("datetime") or stamp.get_text(strip=True), "text": _text(container.get_text(" ", strip=True))})
    return items


def verify_article(row: dict, *, deadline: float) -> dict:
    """重新打开文章，读取正文和原文发布日期，不把 RSS 摘要当证据。"""
    url = row["url"]
    require_article_url(url)
    body = fetch(url, deadline=min(deadline, time.monotonic() + 20))
    soup = BeautifulSoup(body, "html.parser")
    title = soup.find("h1")
    content = soup.find("article") or soup.find("main")
    if title is None or content is None or content not in title.parents:
        raise SourceError("未读取到文章标题和正文，未采用订阅或搜索摘要")
    headline = _text(title.get_text(" ", strip=True))
    for element in soup.select("nav, footer, aside, .related, .recommended"):
        element.decompose()
    stamp = soup.find("meta", attrs={"property": "article:published_time"}) or soup.find("meta", attrs={"name": "date"})
    published = stamp.get("content") if stamp else None
    if not parsed_date(published):
        for candidate in parse_announcements(body, url):
            if (candidate.get("url", "").rstrip("/") == url.rstrip("/")
                    and candidate.get("title") == headline):
                published = candidate.get("published_at")
                break
    if not parsed_date(published):
        heading = title.find_parent("header")
        stamp = heading.find("time") if heading else content.find("time", recursive=False)
        published = stamp.get("datetime") if stamp else None
    if not parsed_date(published):
        raise SourceError("原文发布日期无法确认，未采用 RSS 或搜索日期")
    for element in content.select("script, style, nav, footer, aside, .related, .recommended"):
        element.decompose()
    text = _text(content.get_text(" ", strip=True))
    if len(text) < 8:
        raise SourceError("原文内容不足以支持归纳")
    return {**row, "title": headline, "published_at": published, "text": text, "article_verified": True}


def search_official(base: str, *, deadline: float, now: datetime, attempted: set[str] | None = None) -> list[dict]:
    """Bing 公开 RSS 仅用于找原文；摘要日期不作为发布证据。"""
    domain = (urlparse(base).hostname or "").removeprefix("www.")
    if not domain:
        return []
    query = f"site:{domain} AI after:{(now - timedelta(hours=48)).date().isoformat()}"
    search_url = "https://www.bing.com/search?" + urlencode({"q": query, "format": "rss"})
    candidates = parse_feed(fetch(search_url, deadline=deadline, max_bytes=512000), search_url)
    result, visited = [], set()
    attempted = attempted if attempted is not None else set()
    for candidate in candidates:
        url = valid_url(candidate.get("url"))
        host = (urlparse(url).hostname or "").lower()
        if not url or not (host == domain or host.endswith("." + domain)) or url in visited or url in attempted:
            continue
        visited.add(url)
        if len(visited) > 2 or time.monotonic() >= deadline:
            break
        try:
            # 与直采共用一次原文读取，后续不重复请求同一文章。
            attempted.add(url)
            result.append(verify_article({"url": url}, deadline=deadline))
        except (SourceError, ET.ParseError, TypeError, AttributeError, ValueError):
            continue
    return result


AI_SOURCES = (
    ("GitHub 新建 AI 仓库", "https://api.github.com/search/repositories?q=(AI+OR+LLM+OR+agent)+created:%3E={date}&sort=stars&per_page=20", "github"),
    ("OpenAI", "https://openai.com/news/rss.xml", "feed"),
    ("Anthropic", "https://www.anthropic.com/news", "html"),
    ("智谱", "https://chatglm.cn/blog", "html"),
    ("Kimi", "https://kimi.com/blog", "html"),
    ("X/Twitter", "https://x.com", "search"),
    ("TechCrunch", "https://techcrunch.com/feed/", "feed"),
    ("Hugging Face 博客", "https://huggingface.co/blog/feed.xml", "feed"),
    ("Hugging Face 论文", "https://huggingface.co/api/daily_papers", "papers"),
    ("Google Research", "https://research.google/blog/rss/", "feed"),
    ("机器之心", "https://www.jiqizhixin.com/", "html"),
    ("量子位", "https://www.qbitai.com/feed", "feed"),
)


def collect_ai(*, now: datetime | None = None, deadline: float | None = None) -> dict:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = now - timedelta(hours=48)
    limit = min(deadline or (time.monotonic() + 600), time.monotonic() + 600)
    articles, statuses, seen, attempted = [], [], set(), set()
    for source, template, kind in AI_SOURCES:
        if time.monotonic() >= limit:
            statuses.append({"source": source, "status": "failed", "reason": "达到十分钟采集时限"})
            continue
        url = template.format(date=cutoff.date().isoformat())
        try:
            direct_failed = False
            try:
                body = "" if kind == "search" else fetch(url, deadline=limit)
            except SourceError:
                body, direct_failed = "", True
            if kind == "search":
                rows = []
            elif direct_failed:
                rows = []
            elif kind == "feed":
                rows = parse_feed(body, url)
            elif kind == "html":
                rows = parse_announcements(body, url)
            elif kind == "github":
                payload = json.loads(body)
                if not isinstance(payload.get("items"), list):
                    raise SourceError("GitHub 搜索响应不可用")
                rows = [{"title": item.get("full_name"), "url": item.get("html_url"), "published_at": item.get("created_at"),
                         "text": f"仓库：{item.get('full_name') or '暂未获取'}；仓库顶部描述：{item.get('description') or '暂未获取'}；当前 Star：{item.get('stargazers_count', '暂未获取')}。"}
                        for item in payload["items"] if isinstance(item, dict)]
            else:
                payload = json.loads(body)
                if not isinstance(payload, list):
                    raise SourceError("论文接口响应不可用")
                rows = [{"title": (item.get("paper") or {}).get("title"), "url": f"https://huggingface.co/papers/{(item.get('paper') or {}).get('id', '')}",
                         "published_at": (item.get("paper") or {}).get("publishedAt"), "text": (item.get("paper") or {}).get("summary", "")}
                        for item in payload if isinstance(item, dict)]
            fresh = [row for row in rows if (published := parsed_date(row.get("published_at"))) and cutoff <= published <= now and valid_url(row.get("url"))]
            if not fresh and kind not in {"github", "papers"}:
                try:
                    rows = search_official(url, deadline=limit, now=now, attempted=attempted)
                except (SourceError, ET.ParseError, ValueError):
                    rows = []
            accepted = 0
            rejected = 0
            for row in rows:
                published = parsed_date(row.get("published_at"))
                link = valid_url(row.get("url"))
                if published is None or not cutoff <= published <= now or not link or not row.get("title") or link in seen:
                    continue
                try:
                    require_article_url(link)
                    if kind not in {"github", "papers"} and not row.get("article_verified"):
                        if link in attempted:
                            continue
                        attempted.add(link)
                        row = verify_article({**row, "url": link}, deadline=limit)
                    published = parsed_date(row["published_at"])
                    if published is None or not cutoff <= published <= now:
                        rejected += 1
                        continue
                except (SourceError, ValueError):
                    rejected += 1
                    continue
                seen.add(link)
                articles.append({"id": "S" + hashlib.sha256(link.encode()).hexdigest()[:14], "source": source,
                                 "title": _text(row["title"]), "url": link, "published_at": published.isoformat(), "text": _text(row.get("text"))})
                accepted += 1
                if accepted >= (5 if kind == "github" else 8):
                    break
            reason = (f"{rejected} 条候选未通过原文引用核验" if rejected else "") if accepted else "直接采集与公开搜索未取得近48小时内可验证日期和正文的原文"
            statuses.append({"source": source, "status": "success" if accepted else ("failed" if direct_failed else "empty"), "count": accepted, "reason": reason})
        except (SourceError, json.JSONDecodeError, ET.ParseError, TypeError, AttributeError):
            statuses.append({"source": source, "status": "failed", "reason": "直接采集或公开搜索未取得可验证原文"})
    return {"fetched_at": now.isoformat(), "window_hours": 48, "articles": articles, "sources": statuses}
