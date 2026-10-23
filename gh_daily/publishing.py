"""接入现有 AI 采编工具：仅导入公开内容，仅推送经过检查的阅读产物。"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .build import atomic_text, build_site, load_builder
from .config import REPOSITORY
from .privacy import PATTERNS, check_changes, scan_paths
from .public_content import EditorialContentError, sanitize_editorial_content
from .sync import _SyncLock

REPORT_NAME = re.compile(r"GitHub热点(?:日报_\d{4}-\d{2}-\d{2}|周报_(?:\d{4}-W\d{2}|\d{4}-\d{2}-\d{2})|月报_\d{4}-\d{2})\.html\Z")
AI_NAME = re.compile(r"\d{4}-\d{2}-\d{2}-AI日报\.md\Z")
PUBLIC_PATHS = ["GitHub项目分析", "AI前沿资讯/日报", "dist", "tools/_杂志数据.json", "content-manifest.json"]
MAX_FILE = 16 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
HTML_TAGS = set("html head body title meta style nav main header section footer article div span h1 h2 h3 h4 h5 h6 p br hr table thead tbody tfoot tr th td a strong b em i small ul ol li code pre sup sub blockquote details summary img".split())
HTML_ATTRIBUTES = {"class", "id", "title", "lang", "style", "role", "aria-label", "aria-hidden", "colspan", "rowspan", "scope"}
TAG_ATTRIBUTES = {"a": {"href", "target", "rel"}, "img": {"src", "alt", "width", "height", "loading"}, "meta": {"charset", "name", "content", "http-equiv"}}


class PublishError(ValueError):
    """只含脱敏信息，适合交给调度工具报告。"""


def _incoming(source: Path):
    reports = source / "GitHub项目分析"
    if not reports.is_dir():
        raise PublishError("采编目录缺少 GitHub项目分析，未导入。")
    for file in sorted(reports.glob("*.html")):
        if REPORT_NAME.fullmatch(file.name):
            yield file
    archives = reports / "项目分类库"
    if archives.is_dir():
        for file in sorted(archives.rglob("*.md")):
            yield file
    ai = source / "AI前沿资讯/日报"
    if ai.is_dir():
        for file in sorted(ai.glob("*.md")):
            if AI_NAME.fullmatch(file.name):
                yield file


def _public_text(text: str, *, html: bool) -> str:
    # 历史报告中的本机路径、执行任务编号不属于资讯，公开副本中移除。
    for name, replacement in (("本机用户路径", "[本地路径已移除]"), ("私人任务标识", "[本地任务标识已移除]")):
        if name == "本机用户路径":
            parts = re.split(r"(https?://[^\s<>\"')]+)", text)
            text = "".join(part if re.match(r"https?://", part) else PATTERNS[name].sub(replacement, part) for part in parts)
        else:
            text = PATTERNS[name].sub(replacement, text)
    try:
        text = sanitize_editorial_content(text, html=html)
    except EditorialContentError as error:
        raise PublishError(str(error)) from None
    if not html:
        return text
    soup = BeautifulSoup(text, "html.parser")
    for element in soup.find_all(True):
        if element.attrs is None:
            continue
        if element.name not in HTML_TAGS:
            element.decompose()
            continue
        for attribute in list(element.attrs):
            if attribute not in HTML_ATTRIBUTES | TAG_ATTRIBUTES.get(element.name, set()):
                del element[attribute]
        if element.name == "meta" and str(element.get("http-equiv", "")).lower() == "refresh":
            element.decompose()
            continue
        for attribute in ("href", "src", "action"):
            value = element.get(attribute)
            if isinstance(value, str):
                link = urlsplit(value.strip())
                if link.scheme.lower() not in {"", "http", "https"} or value.lstrip().startswith("//"):
                    del element[attribute]
    return str(soup)


def import_content(root: Path, source: Path) -> dict:
    root, source = Path(root).resolve(), Path(source).expanduser().resolve()
    if root == source:
        raise PublishError("导入目录与公开版目录相同，请直接构建。")
    runtime = root / ".runtime"
    runtime.mkdir(exist_ok=True)
    lock = _SyncLock(runtime / "publication.lock").acquire()
    stage = Path(tempfile.mkdtemp(prefix="import-", dir=runtime))
    previous: dict[Path, bytes | None] = {}
    try:
        builder = load_builder(root)
        count, total = 0, 0
        for file in _incoming(source):
            relative = file.relative_to(source)
            if any(part.startswith(".") for part in relative.parts) or any(parent.is_symlink() for parent in (file, *file.parents) if parent != source.parent):
                raise PublishError("导入内容存在隐藏文件或符号链接，未导入。")
            if file.stat().st_size > MAX_FILE:
                raise PublishError("导入文件超过大小上限。")
            blob = file.read_bytes()
            count += 1
            total += len(blob)
            if count > 2000 or len(blob) > MAX_FILE or total > MAX_TOTAL:
                raise PublishError("导入内容超过文件数或大小上限。")
            try:
                original = blob.decode("utf-8-sig")
            except UnicodeError:
                raise PublishError("导入文件不是有效的 UTF-8 公开资料。") from None
            if any(PATTERNS[name].search(original) for name in ("疑似访问凭据", "私钥正文")):
                raise PublishError("导入资料含疑似凭据，未更改公开版。")
            text = _public_text(original, html=file.suffix == ".html")
            target = stage / relative
            atomic_text(target, text)
            if file.suffix == ".html" and builder.parse_report(target)[0] is None:
                raise PublishError("有报告无法解析为有效榜单，已保留原公开内容。")
        if not count:
            raise PublishError("未发现符合命名规范的公开资料。")
        findings = scan_paths(stage, site_release=True)
        if findings:
            raise PublishError("导入资料未通过隐私检查，未更改公开版：" + "、".join(sorted({x["path"] for x in findings})[:5]))
        for file in sorted(stage.rglob("*")):
            if not file.is_file():
                continue
            target = root / file.relative_to(stage)
            if target.is_symlink() or any(parent.is_symlink() for parent in target.parents if parent != root.parent):
                raise PublishError("公开版目标路径存在符号链接，未导入。")
            blob = file.read_bytes()
            old = target.read_bytes() if target.exists() else None
            if old != blob:
                previous[target] = old
                atomic_text(target, blob.decode("utf-8"))
        build = build_site(root)
        return {"status": "success", "checked": count, "changed": len(previous), "revision": build["revision"]}
    except BaseException:
        for target, old in previous.items():
            if old is None:
                target.unlink(missing_ok=True)
            else:
                atomic_text(target, old.decode("utf-8"))
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
        lock.release()


def _git(root: Path, *args: str, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess:
    environment = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    try:
        result = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-c", "http.version=HTTP/1.1", *args], cwd=root, env=environment, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise PublishError("Git 操作无法完成，请检查 Git 安装、登录和网络；本地内容已保留。") from None
    if check and result.returncode:
        raise PublishError("Git 操作未完成，请检查仓库权限、main 分支及远端状态；未强制覆盖任何内容。")
    return result


def _changed_paths(root: Path) -> list[str]:
    tracked = _git(root, "diff", "--name-only", "-z", "HEAD").stdout
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z").stdout
    return [p for p in (tracked + b"\0" + untracked).decode("utf-8").split("\0") if p]


def _check_outgoing(root: Path) -> None:
    if _git(root, "rev-list", "--merges", "origin/main..HEAD").stdout.strip():
        raise PublishError("待推送历史含合并提交，请人工检查发布；自动发布仅处理线性内容提交。")
    commits = _git(root, "rev-list", "--reverse", "origin/main..HEAD").stdout.decode().splitlines()
    if len(commits) > 20:
        raise PublishError("待推送历史过多，请人工检查后发布。")
    stage = Path(tempfile.mkdtemp(prefix="outgoing-", dir=root / ".runtime"))
    try:
        for commit in commits:
            raw = _git(root, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-z", commit).stdout
            paths = [p for p in raw.decode("utf-8").split("\0") if p]
            if check_changes(root, paths):
                raise PublishError("待推送提交包含代码或配置，请先人工发布；自动发布不会上传这些提交。")
            for name in paths:
                content = _git(root, "show", f"{commit}:{name}", check=False)
                if content.returncode:  # 删除的文件不出现在该提交快照中。
                    continue
                if len(content.stdout) > MAX_FILE:
                    raise PublishError("待推送文件超过大小上限。")
                file = stage / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(content.stdout)
            if scan_paths(stage, site_release=True):
                raise PublishError("待推送历史未通过隐私检查，未上传。")
            shutil.rmtree(stage)
            stage.mkdir()
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def publish_content(root: Path) -> dict:
    root = Path(root).resolve()
    runtime = root / ".runtime"
    runtime.mkdir(exist_ok=True)
    lock = _SyncLock(runtime / "publication.lock").acquire()
    try:
        branch = _git(root, "branch", "--show-current").stdout.decode().strip()
        remote = _git(root, "remote", "get-url", "origin").stdout.decode().strip()
        repository = remote.removeprefix("https://github.com/").removeprefix("git@github.com:").removesuffix(".git")
        if branch != "main" or not REPOSITORY.fullmatch(repository) or remote not in {f"https://github.com/{repository}", f"https://github.com/{repository}.git", f"git@github.com:{repository}.git"}:
            raise PublishError("自动发布仅支持 main 分支及无凭据的 GitHub origin 地址。")
        if check_changes(root, _changed_paths(root)):
            raise PublishError("存在代码、配置或说明文档改动，请先人工处理；自动发布只处理阅读内容。")
        _git(root, "fetch", "--quiet", "origin", "main")
        if _git(root, "merge-base", "--is-ancestor", "origin/main", "HEAD", check=False).returncode:
            raise PublishError("远端已有新提交，请先同步并处理差异；自动发布不会覆盖远端。")
        _check_outgoing(root)
        build_site(root)
        if scan_paths(root, public_release=True) or check_changes(root, _changed_paths(root)):
            raise PublishError("公开内容检查未通过，没有提交或上传。")
        _git(root, "add", "--", *PUBLIC_PATHS)
        changed = _git(root, "diff", "--cached", "--quiet", check=False).returncode
        if changed:
            _git(root, "-c", "user.name=GitHub Daily Press", "-c", "user.email=maintainer@example.invalid", "commit", "-m", "更新公开阅读内容")
        _check_outgoing(root)
        # 即使上次推送失败、这次文件没变化，也重试尚未推送的安全提交。
        _git(root, "push", "origin", "HEAD:main", timeout=180)
        return {"status": "success", "committed": bool(changed), "repository": repository, "message": "公开阅读内容已推送，网站将在 Pages 部署完成后更新。"}
    finally:
        lock.release()
