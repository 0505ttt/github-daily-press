"""只监听回环地址的阅读服务；公开目录与本地配置接口分开处理。"""

from __future__ import annotations

import hmac
import json
import mimetypes
import secrets
import threading
import time
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from . import __version__
from .config import ConfigError, load_config, prepare_config, public_config, save_config
from .models import ModelError, test_connection
from .sync import SyncError, active_site, local_asset, sync_content

MAX_BODY = 16384
CHINA_TIME = timezone(timedelta(hours=8))


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address: tuple, root: Path):
        self.root = root.resolve()
        self.token = secrets.token_urlsafe(32)
        self.operation_lock = threading.Lock()
        self.job = {"running": False, "kind": "", "message": "本地阅读服务已启动。", "ok": True}
        self.stop_event = threading.Event()
        super().__init__(address, LocalHandler)
        self.origin = f"http://127.0.0.1:{self.server_address[1]}"

    def server_close(self):
        self.stop_event.set()
        super().server_close()

    def run_job(self, kind: str) -> bool:
        if not self.operation_lock.acquire(blocking=False):
            return False
        self.job = {"running": True, "kind": kind, "message": "任务正在执行。", "ok": True}

        def execute():
            try:
                if kind == "sync":
                    result = sync_content(self.root)
                else:
                    from .pipeline import run_update
                    result = run_update(self.root)
                    build_status = result.get("tasks", {}).get("build", {}).get("status")
                    if build_status in {"success", "skipped"}:
                        (self.root / ".runtime" / "content" / "active.json").unlink(missing_ok=True)
                succeeded = bool(result.get("ok", False))
                if kind == "sync":
                    message = result.get("message", "任务已完成。")
                elif succeeded:
                    message = "采编已结束，请查看最新内容与采集情况。"
                elif build_status in {"success", "skipped"}:
                    message = "部分采编未完成，已构建的本地内容已生效；请查看采集情况中的失败项。"
                else:
                    message = "采编或构建未完成，继续使用上一版阅读内容；请查看采集情况中的失败项。"
                self.job = {"running": False, "kind": kind, "ok": succeeded,
                            "message": message,
                            "tasks": {name: task.get("status", "failed") for name, task in result.get("tasks", {}).items()},
                            "completed_at": datetime.now(CHINA_TIME).isoformat(timespec="seconds")}
            except (ConfigError, ModelError, SyncError) as error:
                self.job = {"running": False, "kind": kind, "ok": False, "message": str(error)}
            except Exception:
                self.job = {"running": False, "kind": kind, "ok": False,
                            "message": "任务未完成，原有阅读内容仍可使用，请运行诊断命令。"}
            finally:
                self.operation_lock.release()
        threading.Thread(target=execute, daemon=True, name="gh-daily-operation").start()
        return True


class LocalHandler(BaseHTTPRequestHandler):
    server_version = "GH-Daily"
    sys_version = ""

    def log_message(self, format, *args):
        # 默认 HTTP 日志可能记录查询参数和配置错误，故不记录请求内容。
        return

    def _headers(self, status: int, content_type: str = "application/json; charset=utf-8",
                 size: int = 0, cache: str = "no-store"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                         "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
                         "connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()

    def _json(self, status: int, value: dict):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self._headers(status, size=len(body))
        if self.command != "HEAD":
            self.wfile.write(body)

    def _request_allowed(self) -> bool:
        expected = self.server.origin.removeprefix("http://")
        if self.headers.get("Host") != expected:
            return False
        if self.headers.get("Origin") not in {None, self.server.origin}:
            return False
        return self.headers.get("Sec-Fetch-Site") not in {"cross-site"}

    def _path(self) -> str | None:
        path = unquote(urlsplit(self.path).path)
        parts = path.split("/")
        if ("\\" in path or "%" in path or "\x00" in path or
                any(part in {".", ".."} or part.startswith(".") for part in parts if part)):
            return None
        return path

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if not self._request_allowed():
            self._json(403, {"error": "仅允许从本机应用访问。"})
            return
        path = self._path()
        if path is None:
            self._json(400, {"error": "请求路径不正确。"})
            return
        if path == "/api/session":
            self._json(200, {"token": self.server.token})
            return
        if path == "/api/config":
            try:
                self._json(200, public_config())
            except ConfigError as error:
                self._json(400, {"error": str(error)})
            return
        if path == "/api/status":
            site = active_site(self.server.root)
            metadata = {}
            try:
                file = site / "content-manifest.json"
                if file.is_file() and not file.is_symlink() and file.stat().st_size < 1024 * 1024:
                    metadata = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
            self._json(200, {"version": __version__, "online": True, "job": self.server.job,
                             "revision": metadata.get("revision", ""),
                             "generated_at": metadata.get("generated_at", "暂未获取"),
                             "synced": site != self.server.root / "dist"})
            return
        if path.startswith("/api/"):
            self._json(404, {"error": "接口不存在。"})
            return
        relative = path.lstrip("/") or "index.html"
        site = active_site(self.server.root)
        if local_asset(relative):
            site = self.server.root / "dist"
        target = site / relative
        try:
            if (not target.is_file() or any(parent.is_symlink() for parent in (target, *target.parents)
                                          if parent == site or site in parent.parents)
                    or not target.resolve().is_relative_to(site.resolve())):
                self._json(404, {"error": "文件不存在。"})
                return
            size = target.stat().st_size
            kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if target.suffix in {".html", ".css", ".js", ".md", ".json", ".webmanifest", ".svg"}:
                kind += "; charset=utf-8"
            self._headers(200, kind, size, "no-store" if relative.startswith("settings") else "no-cache")
            if self.command != "HEAD":
                with target.open("rb") as source:
                    while chunk := source.read(65536):
                        self.wfile.write(chunk)
        except (OSError, BrokenPipeError):
            self.close_connection = True

    def do_OPTIONS(self):
        self._json(403, {"error": "不允许跨站调用。"})

    def do_POST(self):
        if (not self._request_allowed() or self.headers.get("Origin") != self.server.origin
                or not hmac.compare_digest(self.headers.get("X-GH-Daily-Token", ""), self.server.token)):
            self._json(403, {"error": "会话已失效，请刷新应用后重试。"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if self.headers.get("Transfer-Encoding") or not 1 <= size <= MAX_BODY:
                raise ValueError
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                raise ValueError
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError
        except (ValueError, UnicodeError):
            self._json(400, {"error": "请求必须是大小合理的 JSON 对象。"})
            return
        path = self._path()
        try:
            if path == "/api/config":
                self._json(200, save_config(payload))
            elif path == "/api/test-connection":
                if not self.server.operation_lock.acquire(blocking=False):
                    self._json(409, {"error": "已有任务正在运行，请稍后重试。"})
                    return
                try:
                    self._json(200, test_connection(prepare_config(payload, load_config())))
                finally:
                    self.server.operation_lock.release()
            elif path in {"/api/update", "/api/sync"}:
                if payload:
                    raise ConfigError("此操作不接受额外参数。")
                if self.server.run_job("sync" if path.endswith("sync") else "update"):
                    self._json(202, {"ok": True, "message": "任务已开始，可在状态栏查看结果。"})
                else:
                    self._json(409, {"error": "已有任务正在运行，请稍后重试。"})
            else:
                self._json(404, {"error": "接口不存在。"})
        except (ConfigError, ModelError, SyncError) as error:
            self._json(400, {"error": str(error)})
        except Exception:
            self._json(500, {"error": "本地操作失败，请运行诊断命令。"})


def _maintenance(server: LocalServer, schedule: bool):
    last_sync = 0.0
    last_day = ""
    while not server.stop_event.is_set():
        now = datetime.now(CHINA_TIME)
        today = now.date().isoformat()
        if schedule and (now.hour, now.minute) >= (8, 30) and last_day != today:
            if server.run_job("update"):
                last_day = today
        elif time.monotonic() - last_sync >= 900:
            try:
                if load_config()["source_repo"] and server.run_job("sync"):
                    last_sync = time.monotonic()
                elif not load_config()["source_repo"]:
                    last_sync = time.monotonic()
            except ConfigError:
                last_sync = time.monotonic()
        server.stop_event.wait(20)


def serve(root: Path, port: int = 8765, open_browser: bool = False, schedule: bool = False):
    root = Path(root)
    if not (root / "dist" / "index.html").is_file():
        raise ValueError("尚未构建网页，请先运行构建命令。")
    try:
        server = LocalServer(("127.0.0.1", port), root)
    except OSError:
        raise ValueError(f"端口 {port} 不可用，请关闭占用端口的程序后重试。") from None
    threading.Thread(target=_maintenance, args=(server, schedule), daemon=True,
                     name="gh-daily-maintenance").start()
    print(f"阅读服务已启动：{server.origin}/；按 Ctrl+C 停止。")
    if open_browser:
        webbrowser.open(server.origin + "/")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("阅读服务已停止；已缓存的内容仍可离线阅读。")
    finally:
        server.server_close()
