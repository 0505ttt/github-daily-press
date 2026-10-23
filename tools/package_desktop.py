#!/usr/bin/env python3
"""在对应系统上构建真实桌面应用，产物只写入本地运行目录。"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gh_daily import __version__
from gh_daily.build import build_site
from gh_daily.privacy import scan_paths

APP_NAME = "GitHubDailyPress"
WORK = ROOT / ".runtime/desktop"


def run(command):
    subprocess.run([str(item) for item in command], cwd=ROOT, check=True)


def license_texts() -> str:
    sections = ["桌面安装包所含第三方依赖的权利说明\n本项目代码采用 MIT；以下依赖保留各自许可。\n"]
    for distribution in sorted(importlib.metadata.distributions(), key=lambda item: item.metadata["Name"].lower()):
        name = distribution.metadata["Name"]
        for relative in distribution.files or []:
            if (Path(relative).name.upper().startswith(("LICENSE", "COPYING"))
                    and Path(relative).suffix.lower() in {"", ".txt", ".md", ".rst"}):
                file = distribution.locate_file(relative)
                if file.is_file() and file.stat().st_size < 512 * 1024:
                    text = file.read_text(encoding="utf-8", errors="replace")
                    if "\x00" in text:
                        continue
                    sections.append(f"\n{'=' * 60}\n{name} {distribution.version} / {Path(relative).name}\n{text}\n")
    return "\n".join(sections)


def prepare_payload(source_root: Path = ROOT, work_root: Path = WORK) -> Path:
    """桌面种子只带程序资源，在独立目录构建零期站点，不读取公开仓库历史。"""
    payload = work_root / "payload"
    if payload.exists():
        shutil.rmtree(payload)
    payload.mkdir(parents=True)
    source_files = [path for path in (source_root / "web").rglob("*") if path.is_file()]
    source_files.extend(source_root / name for name in ("tools/build_magazine.py", "README.md", "LICENSE", "NOTICE.md",
                                                       "数据来源.md"))
    for source in sorted(set(source_files)):
        if source.is_symlink():
            raise ValueError("打包输入不能是符号链接。")
        if not source.is_file():
            continue
        target = payload / source.relative_to(source_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (payload / "THIRD-PARTY-LICENSES.txt").write_text(license_texts(), encoding="utf-8")
    build_site(payload, allow_empty=True)
    # 构建临时目录与导入字节码既不属于种子，也不应携带构建机路径。
    shutil.rmtree(payload / ".runtime", ignore_errors=True)
    for cache in list(payload.rglob("__pycache__")):
        shutil.rmtree(cache)
    findings = scan_paths(payload)
    if findings:
        raise ValueError("桌面种子隐私检查未通过。")
    files = []
    for file in sorted(payload.rglob("*")):
        if file.is_file():
            data = file.read_bytes()
            files.append({"path": file.relative_to(payload).as_posix(), "size": len(data),
                          "sha256": hashlib.sha256(data).hexdigest()})
    revision = hashlib.sha256(json.dumps(files, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    (payload / "desktop-seed.json").write_text(json.dumps({"version": __version__, "mode": "empty-local", "revision": revision,
                                                           "files": files}, ensure_ascii=False), encoding="utf-8")
    return payload


def build_executable(payload: Path) -> Path:
    from PIL import Image
    icon = WORK / ("application.icns" if sys.platform == "darwin" else "application.ico")
    with Image.open(ROOT / "web/icons/icon-512.png") as image:
        image.save(icon)
    output = WORK / "bundle"
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--onedir",
               "--name", APP_NAME, "--distpath", output, "--workpath", WORK / "pyinstaller",
               "--specpath", WORK, "--paths", ROOT, "--icon", icon,
               "--add-data", f"{payload}{os.pathsep}desktop_payload",
               "--collect-submodules", "gh_daily", "--collect-data", "certifi", "--collect-data", "tzdata",
               "--collect-all", "webview", "--exclude-module", "PyQt5", "--exclude-module", "PyQt6",
               "--exclude-module", "PySide2", "--exclude-module", "PySide6"]
    if sys.platform == "darwin":
        command.extend(["--osx-bundle-identifier", "io.github.githubdaily.press"])
    command.append(ROOT / "tools/desktop_entry.py")
    run(command)
    if sys.platform == "darwin":
        return output / (APP_NAME + ".app")
    return output / APP_NAME


def verify_bundle(bundle: Path) -> None:
    binary = bundle / ("Contents/MacOS/" + APP_NAME if sys.platform == "darwin" else APP_NAME + ".exe")
    report = WORK / "frozen-self-test.json"
    report.unlink(missing_ok=True)
    run([binary, "--self-test", "--report", report])
    if not json.loads(report.read_text(encoding="utf-8")).get("ok"):
        raise ValueError("冻结桌面应用自检未通过。")


def package(bundle: Path) -> list[Path]:
    artifacts = WORK / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    architecture = "arm64" if platform.machine().lower() in {"arm64", "aarch64"} else "x64"
    stem = f"{APP_NAME}-{__version__}"
    if sys.platform == "darwin":
        stage = WORK / "dmg-content"
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir()
        shutil.copytree(bundle, stage / bundle.name, symlinks=True)
        (stage / "Applications").symlink_to("/Applications")
        destination = artifacts / f"{stem}-macos-{architecture}.dmg"
        destination.unlink(missing_ok=True)
        run(["hdiutil", "create", "-volname", APP_NAME, "-srcfolder", stage,
             "-ov", "-format", "UDZO", destination])
        return [destination]
    compiler = shutil.which("iscc") or str(Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
                                          / "Inno Setup 6/ISCC.exe")
    run([compiler, f"/DAppVersion={__version__}", f"/DBundleDir={bundle}", f"/DOutputDir={artifacts}",
         ROOT / "tools/windows-installer.iss"])
    archive = Path(shutil.make_archive(str(artifacts / f"{stem}-windows-x64-portable"), "zip", bundle.parent, bundle.name))
    return [artifacts / f"{stem}-windows-x64-setup.exe", archive]


def main() -> int:
    parser = argparse.ArgumentParser(description="构建 Mac/Windows 桌面安装包")
    parser.add_argument("--payload-only", action="store_true", help="仅准备并验证公开种子")
    args = parser.parse_args()
    if sys.platform not in {"darwin", "win32"} and not args.payload_only:
        parser.error("桌面包必须在对应的 macOS 或 Windows 系统构建。")
    payload = prepare_payload()
    if args.payload_only:
        print("桌面公开种子已准备并通过隐私检查。")
        return 0
    bundle = build_executable(payload)
    verify_bundle(bundle)
    outputs = package(bundle)
    for file in outputs:
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        file.with_suffix(file.suffix + ".sha256").write_text(f"{digest}  {file.name}\n", encoding="utf-8")
        print(file.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
