"""捆绑运行时的桌面入口：应用自启本机服务，窗口关闭后停止服务。"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import tempfile
import threading
from pathlib import Path, PurePosixPath
from urllib.request import urlopen

from . import __version__
from .server import LocalServer, _maintenance
from .sync import SyncError, _SyncLock

APP_TITLE = "GitHub 每日项目推送"
SEED_NAME = "desktop-seed.json"


class DesktopError(ValueError):
    """可以安全显示的桌面启动错误。"""


def bundled_payload() -> Path:
    if getattr(sys, "frozen", False):
        # macOS .app 把数据放在 Resources，并从 Frameworks 建立打包器自身的链接。
        return (Path(sys._MEIPASS) / "desktop_payload").resolve()
    return Path(__file__).resolve().parents[1] / ".runtime/desktop/payload"


def desktop_directory() -> Path:
    if os.environ.get("GH_DAILY_DATA_DIR"):
        return Path(os.environ["GH_DAILY_DATA_DIR"]).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    return base / "GitHubDailyPress"


def _safe_child(base: Path, relative: str) -> Path:
    parts = PurePosixPath(relative).parts
    if (not parts or relative.startswith("/") or "\\" in relative or ":" in relative
            or "/".join(parts) != relative or any(x in {".", ".."} for x in parts)):
        raise DesktopError("桌面资源路径不正确，请重新下载安装包。")
    child = base.joinpath(*parts)
    if any(path.is_symlink() for path in (base, child, *child.parents) if path == base or base in path.parents):
        raise DesktopError("桌面数据目录存在符号链接，请移除链接后重试。")
    return child


def seed_manifest(payload: Path) -> dict:
    try:
        manifest = json.loads((payload / SEED_NAME).read_text(encoding="utf-8"))
        files = manifest["files"]
        if (manifest["version"] != __version__ or manifest.get("mode") != "empty-local"
                or not isinstance(files, list) or not 1 <= len(files) <= 3000
                or not isinstance(manifest.get("revision"), str)):
            raise ValueError
        seen = set()
        for entry in files:
            relative = entry["path"]
            if relative in seen:
                raise ValueError
            seen.add(relative)
            file = _safe_child(payload, relative)
            if (not file.is_file() or file.stat().st_size != entry["size"]
                    or hashlib.sha256(file.read_bytes()).hexdigest() != entry["sha256"]):
                raise ValueError
        if "dist/index.html" not in seen or "tools/build_magazine.py" not in seen:
            raise ValueError
        return manifest
    except (OSError, ValueError, TypeError, KeyError):
        raise DesktopError("桌面资源校验失败，请重新下载安装包。") from None


def prepare_workspace(payload: Path, directory: Path) -> Path:
    """从经哈希验证的空白种子初始化；升级时保留用户自己的日报和档案。"""
    manifest = seed_manifest(payload)
    if directory.is_symlink():
        raise DesktopError("桌面数据目录不能是符号链接。")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    root = _safe_child(directory, "workspace")
    installed = _safe_child(root, SEED_NAME)
    previous_revision = ""
    if installed.is_file() and not installed.is_symlink():
        try:
            previous_revision = json.loads(installed.read_text(encoding="utf-8"))["revision"]
        except (OSError, ValueError, KeyError):
            pass
    fresh = not root.exists()
    if previous_revision == manifest["revision"] and (root / "dist/index.html").is_file():
        return root
    root.mkdir(mode=0o700, exist_ok=True)
    for entry in manifest["files"]:
        relative = entry["path"]
        target = _safe_child(root, relative)
        program_resource = relative.startswith(("web/", "tools/")) or "/" not in relative
        if not fresh and relative.startswith("dist/"):
            continue
        if fresh or program_resource or not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=".desktop-", dir=target.parent)
            try:
                with os.fdopen(descriptor, "wb") as output:
                    output.write((payload / relative).read_bytes())
                os.replace(temporary, target)
            finally:
                Path(temporary).unlink(missing_ok=True)
    if not fresh:
        from .build import build_site
        build_site(root, allow_empty=True)
    installed.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return root


def _show_error(message: str) -> None:
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, APP_TITLE, 0x10)
    elif sys.platform == "darwin":
        from Cocoa import NSAlert, NSApplication
        NSApplication.sharedApplication()
        alert = NSAlert.alloc().init()
        alert.setMessageText_(APP_TITLE)
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_("关闭")
        alert.runModal()
    elif sys.stderr is not None:
        sys.stderr.write(message + "\n")


def run_window(root: Path, storage: Path) -> None:
    try:
        server = LocalServer(("127.0.0.1", 8765), root)
    except OSError:
        raise DesktopError("端口 8765 已被占用。请先退出另一个本应用或本地阅读服务，再重新打开。") from None
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.25},
                              daemon=True, name="gh-daily-desktop-http")
    worker.start()
    threading.Thread(target=_maintenance, args=(server, False), daemon=True,
                     name="gh-daily-desktop-maintenance").start()
    try:
        import webview
        # 浏览引擎的异常可能含目标 URL；不将其写入公开文件或本地日志。
        logging.getLogger("pywebview").disabled = True
        webview.settings["ALLOW_FILE_URLS"] = False
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        webview.settings["SHOW_DEFAULT_MENUS"] = False
        webview.create_window(APP_TITLE, server.origin + "/", width=1440, height=940,
                              min_size=(360, 540), maximized=True, background_color="#24292e",
                              text_select=True, zoomable=True)
        storage.mkdir(parents=True, exist_ok=True, mode=0o700)
        webview.start(gui="edgechromium" if os.name == "nt" else "cocoa",
                      debug=False, private_mode=False, storage_path=str(storage))
    finally:
        server.stop_event.set()
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def self_test(payload: Path) -> dict:
    """对冻结产物执行无界面的资源和实际 HTTP 回归；不进行云端连接。"""
    import webview  # 确认冻结包包含桌面依赖，但不启动 GUI。
    with tempfile.TemporaryDirectory(prefix="gh-daily-desktop-test-") as temporary:
        root = prepare_workspace(payload, Path(temporary) / "app")
        from .build import build_site, load_builder
        build_site(root, allow_empty=True)
        database, _, _ = load_builder(root).build_db()
        if database["issues"] or database["projects"] or database["ai_days"]:
            raise DesktopError("桌面安装包不应包含已有日报或档案。")
        server = LocalServer(("127.0.0.1", 0), root)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with urlopen(server.origin + "/", timeout=5) as response:
                ok = response.status == 200 and b"<!doctype html>" in response.read().lower()
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)
    return {"ok": ok, "version": __version__, "desktop_dependency": bool(webview),
            "checks": ["公开种子哈希", "空白资料库", "可写数据目录", "冻结环境完整构建", "回环 HTTP 读取"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=APP_TITLE + "桌面应用")
    parser.add_argument("--self-test", action="store_true", help="仅运行冻结包自检")
    parser.add_argument("--report", type=Path, help="将自检结果保存为 JSON")
    args = parser.parse_args(argv)
    if args.self_test:
        try:
            report = self_test(bundled_payload())
        except Exception:
            report = {"ok": False, "version": __version__, "error": "桌面包自检未通过。"}
        if args.report:
            args.report.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        elif sys.stdout is not None:
            sys.stdout.write(json.dumps(report, ensure_ascii=False) + "\n")
        return 0 if report["ok"] else 1
    lock = None
    try:
        directory = desktop_directory()
        if directory.is_symlink():
            raise DesktopError("桌面数据目录不能是符号链接。")
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = _SyncLock(directory / "application.lock").acquire()
        root = prepare_workspace(bundled_payload(), directory)
        run_window(root, directory / "webview")
        return 0
    except DesktopError as error:
        message = str(error)
    except SyncError:
        message = "本应用已经启动，请返回已打开的应用窗口。"
    except Exception:
        message = "桌面应用启动未完成。请重新安装；Windows 请确认已安装 Microsoft Edge WebView2 Runtime。"
    finally:
        if lock is not None:
            lock.release()
    try:
        _show_error(message)
    except Exception:
        if sys.stderr is not None:
            sys.stderr.write(message + "\n")
    return 1
