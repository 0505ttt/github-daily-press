"""从公开历史构建离线杂志及受限静态站点。"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

DATA_DIRS = ("GitHub项目分析", "AI前沿资讯")
DATA_SUFFIXES = {".html", ".md", ".pdf"}
INTRO_IMAGE_SUFFIXES = {".svg", ".png", ".jpg", ".jpeg"}


def load_builder(root: Path):
    spec = importlib.util.spec_from_file_location("gh_daily_magazine_builder", root / "tools/build_magazine.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("未找到杂志构建脚本，请从完整项目目录运行。")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def public_data_files(root: Path):
    for directory in DATA_DIRS:
        base = root / directory
        if not base.exists():
            continue
        for file in sorted(base.rglob("*")):
            if file.is_symlink():
                raise ValueError("公开数据中存在符号链接，请移除后重建。")
            if file.is_file() and file.suffix.lower() in DATA_SUFFIXES and file.name != "IDEA.md":
                yield file


def public_intro_files(root: Path):
    """仅发布介绍页及其公开配图，不复制整份文档目录。"""
    docs = root / "docs"
    intro = docs / "项目介绍.html"
    images = docs / "images"
    for path in (docs, intro, images):
        if path.is_symlink():
            raise ValueError("项目介绍资源不能使用符号链接。")
    if intro.is_file():
        yield intro
    if images.is_dir():
        for file in sorted(images.rglob("*")):
            if file.is_symlink():
                raise ValueError("项目介绍资源不能使用符号链接。")
            relative = file.relative_to(images)
            if any(part.startswith(".") for part in relative.parts):
                continue
            if file.is_file() and file.suffix in INTRO_IMAGE_SUFFIXES:
                yield file


def build_site(root: Path, *, hosted: bool = False, base_path: str = "/", allow_empty: bool = False) -> dict:
    if not re.fullmatch(r"/(?:[A-Za-z0-9_-][A-Za-z0-9_.-]*/)*", base_path):
        raise ValueError("网站路径必须以 / 开始和结束，且不能含跳转或查询参数。")
    if not hosted and base_path != "/":
        raise ValueError("本地应用固定使用根路径；子路径仅供在线网站构建。")
    root = Path(root).resolve()
    builder = load_builder(root)
    db, logs, skipped = builder.build_db()
    if not db["issues"] and (not allow_empty or skipped):
        raise ValueError("未解析到任何有效报告，保留上一版产物。")
    html = builder.render_html(db)
    json_data = json.dumps(db, ensure_ascii=False, indent=1)
    stage = Path(tempfile.mkdtemp(prefix="site-", dir=root / ".runtime")) if (root / ".runtime").exists() else None
    if stage is None:
        (root / ".runtime").mkdir()
        stage = Path(tempfile.mkdtemp(prefix="site-", dir=root / ".runtime"))
    try:
        for file in public_data_files(root):
            target = stage / file.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target)
        for file in public_intro_files(root):
            target = stage / file.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target)
        for name in ("补档说明.md", "数据来源.md", "README.md"):
            if (root / name).is_file():
                shutil.copyfile(root / name, stage / name)
        atomic_text(stage / "GitHub项目分析/GitHub热点杂志.html", html)
        for file in sorted((root / "web").rglob("*")):
            if file.is_symlink():
                raise ValueError("网页资源不能使用符号链接。")
            if file.is_file():
                if hosted and file.relative_to(root / "web").as_posix() in {"settings.html", "settings.js"}:
                    continue
                target = stage / file.relative_to(root / "web")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file, target)
        atomic_text(stage / "site-config.json", json.dumps({"mode": "hosted" if hosted else "local", "base_path": base_path}, ensure_ascii=False))
        manifest_path = stage / "manifest.webmanifest"
        if manifest_path.is_file():
            app_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            app_manifest.update(id=base_path, scope=base_path, start_url=base_path + "GitHub项目分析/GitHub热点杂志.html")
            for icon in app_manifest.get("icons", []):
                icon["src"] = base_path + icon["src"].lstrip("/")
            atomic_text(manifest_path, json.dumps(app_manifest, ensure_ascii=False, indent=2) + "\n")
        atomic_text(stage / "index.html", '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=GitHub项目分析/GitHub热点杂志.html"><title>正在打开杂志</title><a href="GitHub项目分析/GitHub热点杂志.html">打开 GitHub 热点杂志</a></html>')
        offline_help = "请联网打开网站并等待显示“可离线阅读”。" if hosted else "请启动本地服务，连线打开杂志并等待显示“可离线阅读”。"
        atomic_text(stage / "offline.html", '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>离线阅读</title><h1>当前内容尚未缓存</h1><p>' + offline_help + '</p><a href="' + base_path + '">返回杂志</a></html>')
        files = []
        for file in sorted(stage.rglob("*")):
            if file.is_file():
                blob = file.read_bytes()
                files.append({"path": file.relative_to(stage).as_posix(), "sha256": hashlib.sha256(blob).hexdigest(), "size": len(blob)})
        revision = hashlib.sha256(json.dumps(files, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
        manifest = {"revision": revision, "generated_at": db["generated_at"], "files": files}
        atomic_text(stage / "content-version.json", json.dumps({"revision": revision, "generated_at": db["generated_at"]}, ensure_ascii=False))
        version_file = stage / "content-version.json"
        blob = version_file.read_bytes()
        files.append({"path": "content-version.json", "sha256": hashlib.sha256(blob).hexdigest(), "size": len(blob)})
        serialized = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        atomic_text(stage / "content-manifest.json", serialized)
        from .privacy import scan_paths
        findings = scan_paths(stage, site_release=True)
        if findings:
            raise ValueError("公开站点隐私检查未通过：" + "、".join(sorted({x["path"] for x in findings})[:5]))
        target = root / "dist"
        backup = root / ".runtime/previous-dist"
        updates = {
            root / "content-manifest.json": serialized,
            root / "GitHub项目分析/GitHub热点杂志.html": html,
            root / "tools/_杂志数据.json": json_data,
        }
        if hosted:
            # 在线构建只替换 dist，不改变本地同步使用的清单和单文件源产物。
            updates = {}
        previous = {path: path.read_text(encoding="utf-8") if path.exists() else None for path in updates}
        if backup.exists():
            shutil.rmtree(backup)
        moved_old = False
        installed_new = False
        try:
            for path, content in updates.items():
                atomic_text(path, content)
            if target.exists():
                os.replace(target, backup)
                moved_old = True
            os.replace(stage, target)
            installed_new = True
        except BaseException:
            if installed_new and target.exists():
                shutil.rmtree(target)
            if moved_old:
                os.replace(backup, target)
            for path, content in previous.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_text(path, content)
            raise
        return {"status": "success", "revision": revision, "files": len(files), "meta": db["meta"], "skipped": skipped}
    finally:
        if stage.exists():
            shutil.rmtree(stage)
