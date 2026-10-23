"""发布白名单与隐私扫描；报告仅含路径和规则名。"""
from __future__ import annotations

import json
import hashlib
import os
import re
from pathlib import Path

SKIP = {".git", ".venv", ".runtime", ".codegraph", ".codegraph-tools", "__pycache__", "test-results", "build", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
PATTERNS = {
    "本机用户路径": re.compile(r"/(?:Users|home)/[^\s<>\"']+|[A-Za-z]:\\Users\\[^\s<>\"']+"),
    "私人任务标识": re.compile(r"(?:automation-|sess_)[0-9a-f][0-9a-f-]{15,}", re.I),
    "疑似访问凭据": re.compile(r"(?:ghp_|github_pat_|sk-)[A-Za-z0-9_-]{20,}"),
    "私钥正文": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
TEXT_SUFFIXES = {".md", ".html", ".json", ".py", ".js", ".css", ".toml", ".yml", ".yaml", ".txt", ".svg", ".webmanifest", ".command", ".ps1"}
FILE_SUFFIXES = TEXT_SUFFIXES | {".png", ".jpg", ".jpeg", ".pdf", ".ico", ".bat"}
SPECIAL_FILES = {"LICENSE", ".gitignore", ".gitattributes", ".env.example"}
SITE_SUFFIXES = {".html", ".md", ".pdf", ".css", ".js", ".json", ".txt", ".svg", ".webmanifest", ".png", ".jpg", ".jpeg", ".ico"}
ALLOWED_TOP = {"AGENTS.md", "README.md", "LICENSE", "CONTRIBUTING.md", "CHANGELOG.md", "SECURITY.md", "NOTICE.md", "pyproject.toml", ".gitignore", ".gitattributes", ".env.example", "启动.command", "启动.ps1", "启动.bat", "content-manifest.json", "数据来源.md", "补档说明.md", "gh_daily", "web", "tools", "tests", "docs", ".github", "GitHub项目分析", "AI前沿资讯", "dist"}
_PDF_TEXT_CACHE: dict[str, str] = {}


def scan_paths(root: Path, *, public_release: bool = False, site_release: bool = False) -> list[dict]:
    root = Path(root)
    site_release = site_release or root.name == "dist"
    findings = []
    markers = [s for s in os.environ.get("GH_DAILY_PRIVATE_MARKERS", "").split(",") if s.strip()]
    for file in sorted(root.rglob("*")):
        rel = file.relative_to(root)
        if not site_release and (rel.parts[0] in SKIP or rel.parts[0].endswith(".egg-info")):
            continue
        if not site_release and "__pycache__" in rel.parts and rel.parts[0] in {"gh_daily", "tools", "tests"}:
            continue
        if file.is_symlink():
            findings.append({"path": rel.as_posix(), "rule": "符号链接"})
            continue
        if not file.is_file():
            continue
        if public_release and rel.parts[0] not in ALLOWED_TOP:
            findings.append({"path": rel.as_posix(), "rule": "不在发布白名单"})
        if public_release and file.suffix not in FILE_SUFFIXES and file.name not in SPECIAL_FILES:
            findings.append({"path": rel.as_posix(), "rule": "未允许的文件类型"})
        if site_release and (file.suffix not in SITE_SUFFIXES or any(part.startswith(".") for part in rel.parts)):
            findings.append({"path": rel.as_posix(), "rule": "未允许的站点文件"})
        if file.name.startswith(".env") and file.name != ".env.example":
            findings.append({"path": rel.as_posix(), "rule": "私人环境配置"})
        if file.suffix == ".pdf":
            from pypdf import PdfReader
            try:
                fingerprint = hashlib.sha256(file.read_bytes()).hexdigest()
                text = _PDF_TEXT_CACHE.get(fingerprint)
                if text is None:
                    reader = PdfReader(file)
                    text = "\n".join((page.extract_text() or "") for page in reader.pages)
                    text += json.dumps(dict(reader.metadata or {}), ensure_ascii=False)
                    _PDF_TEXT_CACHE[fingerprint] = text
            except Exception:
                findings.append({"path": rel.as_posix(), "rule": "PDF无法检查"})
                continue
        elif file.suffix in TEXT_SUFFIXES | {".bat"} or file.name in SPECIAL_FILES:
            text = file.read_text(encoding="utf-8", errors="replace")
        else:
            continue
        for name, pattern in PATTERNS.items():
            # 公告网站可能合法包含 /news/home/ 等路径，不能当成本机目录。
            candidate = re.sub(r"https?://[^\s<>\"')]+", "", text) if name == "本机用户路径" else text
            if pattern.search(candidate):
                findings.append({"path": rel.as_posix(), "rule": name})
        if any(marker in text for marker in markers):
            findings.append({"path": rel.as_posix(), "rule": "自定义私人标识"})
    return findings


def check_changes(root: Path, paths: list[str]) -> list[str]:
    """云端只允许报告与明确的构建产物进入自动提交。"""
    bad = []
    for value in paths:
        path = Path(value)
        safe = not path.is_absolute() and ".." not in path.parts
        allowed = value == "content-manifest.json" or value == "tools/_杂志数据.json"
        allowed |= bool(path.parts and path.parts[0] == "GitHub项目分析" and path.suffix in {".html", ".md"})
        allowed |= value.startswith("AI前沿资讯/日报/") and path.suffix == ".md"
        allowed |= value.startswith("dist/") and path.suffix in TEXT_SUFFIXES | {".png", ".pdf", ".ico"}
        if not safe or not allowed or (root / path).is_symlink():
            bad.append(value)
    return bad
