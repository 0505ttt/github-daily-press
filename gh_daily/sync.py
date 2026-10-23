"""按哈希清单同步公开阅读产物，不运行 Git，也不覆盖源代码或用户配置。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from .config import REPOSITORY, load_config
from .models import _addresses, _PinnedHTTPS

MAX_FILES = 2000
MAX_TOTAL = 64 * 1024 * 1024
MAX_FILE = 16 * 1024 * 1024
ROOT_FILES = {"index.html", "offline.html", "app.css", "pwa.js", "sw.js",
              "manifest.webmanifest", "settings.html", "settings.js", "content-version.json",
              "补档说明.md", "数据来源.md"}
LOCAL_ASSETS = {"settings.html", "settings.js", "pwa.js", "app.css", "sw.js", "manifest.webmanifest"}


def local_asset(path: str) -> bool:
    return path in LOCAL_ASSETS or path.startswith(("icons/", "assets/"))


class SyncError(ValueError):
    """不会包含路径或网络响应的公开错误。"""


class _SyncLock:
    """文件保留，互斥状态由内核维护；进程强退也会释放。"""

    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def acquire(self):
        if self.path.is_symlink():
            raise SyncError("同步锁文件不能是符号链接。")
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        self.handle = os.fdopen(descriptor, "r+b")
        try:
            if os.name == "nt":
                import msvcrt
                if self.handle.seek(0, os.SEEK_END) == 0:
                    self.handle.write(b"0")
                    self.handle.flush()
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            self.handle = None
            raise SyncError("已有同步任务正在运行，请稍后重试。") from None
        return self

    def release(self):
        if self.handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None


def allowed_content_path(path: str) -> bool:
    if not isinstance(path, str) or not path or len(path) > 500 or "\\" in path or "%" in path:
        return False
    parts = PurePosixPath(path).parts
    if path.startswith("/") or any(part.startswith(".") or ":" in part for part in parts):
        return False
    if "/".join(parts) != path or ".." in parts:
        return False
    if path in ROOT_FILES:
        return True
    if parts[0] in {"icons", "assets"}:
        return len(parts) > 1 and Path(path).suffix.lower() in {".png", ".svg", ".ico", ".webp", ".jpg", ".css", ".js"}
    if parts[0] == "GitHub项目分析":
        return len(parts) > 1 and Path(path).suffix.lower() in {".html", ".md", ".pdf"}
    return len(parts) == 3 and parts[:2] == ("AI前沿资讯", "日报") and path.endswith(".md")


def _download(path: str, maximum: int) -> bytes:
    host = "raw.githubusercontent.com"
    connection = _PinnedHTTPS(host, _addresses(host, 443)[0], 443, 30)
    try:
        connection.request("GET", path, headers={"Accept": "application/octet-stream", "User-Agent": "gh-daily/1.0"})
        response = connection.getresponse()
        if response.status != 200:
            raise SyncError("公开仓库文件暂时不可用，请确认仓库、main 分支及发布清单。")
        data = response.read(maximum + 1)
        if len(data) > maximum:
            raise SyncError("同步文件超过大小上限。")
        return data
    except SyncError:
        raise
    except Exception:
        raise SyncError("同步连接失败，请检查网络后重试。") from None
    finally:
        connection.close()


def active_site(root: Path) -> Path:
    """指针只允许指向内容目录内的完整、非链接版本。"""
    base = root / ".runtime" / "content"
    pointer = base / "active.json"
    try:
        if pointer.is_symlink() or pointer.stat().st_size > 4096:
            return root / "dist"
        directory = json.loads(pointer.read_text(encoding="utf-8"))["directory"]
        if not re.fullmatch(r"[a-f0-9]{64}", directory):
            return root / "dist"
        site = base / directory
        if site.is_symlink() or not (site / "content-manifest.json").is_file():
            return root / "dist"
        return site
    except (OSError, ValueError, TypeError, KeyError):
        return root / "dist"


def sync_content(root: Path, repo: str | None = None) -> dict:
    root = Path(root)
    repository = repo if repo is not None else load_config()["source_repo"]
    if not repository:
        return {"ok": True, "changed": False, "message": "尚未配置来源仓库，可继续阅读本地内容。"}
    if not REPOSITORY.fullmatch(repository):
        raise SyncError("仓库格式不正确，请填写 owner/repo。")
    prefix = "/" + repository + "/main/"
    manifest_bytes = _download(prefix + "content-manifest.json", 1024 * 1024)
    try:
        manifest = json.loads(manifest_bytes)
        files, revision = manifest["files"], manifest["revision"]
        if (not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES
                or not isinstance(revision, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", revision)):
            raise ValueError
        total, seen = 0, set()
        for entry in files:
            path, digest, size = entry["path"], entry["sha256"], entry["size"]
            if (not allowed_content_path(path) or path in seen
                    or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)
                    or type(size) is not int or not 0 <= size <= MAX_FILE):
                raise ValueError
            seen.add(path)
            total += size
        if total > MAX_TOTAL or "GitHub项目分析/GitHub热点杂志.html" not in seen:
            raise ValueError
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise SyncError("同步清单不符合公开阅读文件规范。") from None
    base = root / ".runtime" / "content"
    if any(parent.is_symlink() for parent in (root / ".runtime", base)):
        raise SyncError("运行时目录不能是符号链接。")
    base.mkdir(parents=True, exist_ok=True)
    identity_hash = hashlib.sha256(manifest_bytes)
    local_bytes = {}
    for entry in files:
        if local_asset(entry["path"]):
            local = root / "dist" / entry["path"]
            if not local.is_file() or local.is_symlink() or local.stat().st_size > MAX_FILE:
                raise SyncError("本机应用资源不完整，请先重新构建应用。")
            data = local.read_bytes()
            local_bytes[entry["path"]] = data
            identity_hash.update(entry["path"].encode("utf-8"))
            identity_hash.update(hashlib.sha256(data).digest())
    identity = identity_hash.hexdigest()
    target = base / identity
    if active_site(root) == target:
        return {"ok": True, "changed": False, "revision": revision, "message": "阅读内容已是最新版本。"}
    lock = _SyncLock(base / ".sync.lock").acquire()
    stage = None
    try:
        if active_site(root) == target:
            return {"ok": True, "changed": False, "revision": revision, "message": "阅读内容已是最新版本。"}
        stage = Path(tempfile.mkdtemp(prefix=".download-", dir=base))
        for entry in files:
            data = _download(prefix + "dist/" + quote(entry["path"], safe="/"), entry["size"])
            if len(data) != entry["size"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise SyncError("同步文件校验失败，已保留上一版阅读内容。")
            destination = stage / entry["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        # 阅读内容可更新，应用实现仍来自本机版本；缓存清单必须描述实际服务的字节。
        effective = dict(manifest)
        effective["files"] = [dict(entry) for entry in files]
        for entry in effective["files"]:
            if local_asset(entry["path"]):
                data = local_bytes[entry["path"]]
                entry.update(sha256=hashlib.sha256(data).hexdigest(), size=len(data))
        effective["upstream_revision"] = revision
        effective["revision"] = hashlib.sha256(json.dumps(effective["files"], sort_keys=True,
                                                           ensure_ascii=False).encode()).hexdigest()[:24]
        (stage / "content-manifest.json").write_text(json.dumps(effective, ensure_ascii=False), encoding="utf-8")
        if target.exists():
            if target.is_symlink():
                raise SyncError("运行时版本不能是符号链接。")
            shutil.rmtree(target)
        os.replace(stage, target)
        pointer = base / (".active-" + identity + ".json")
        pointer.write_text(json.dumps({"directory": identity, "revision": revision,
                                       "synced_at": int(time.time())}), encoding="utf-8")
        os.replace(pointer, base / "active.json")
        return {"ok": True, "changed": True, "revision": revision,
                "files": len(files), "message": "公开阅读内容已同步，刷新后查看。"}
    finally:
        try:
            if stage is not None and stage.exists():
                shutil.rmtree(stage)
        finally:
            lock.release()
