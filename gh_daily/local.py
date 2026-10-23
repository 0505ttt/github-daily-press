"""源码本地启动使用独立、持久的空白刊物，和公开仓库历史分开。"""
from __future__ import annotations

import os
from pathlib import Path

from .build import build_site
from .desktop import desktop_directory
from .sync import _SyncLock


def prepare_local_workspace(source: Path) -> Path:
    data_dir = Path(os.environ.get("GH_DAILY_DATA_DIR", str(desktop_directory()))).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = _SyncLock(data_dir / "workspace-init.lock").acquire()
    root = data_dir / "workspace"
    try:
        if root.is_symlink():
            raise ValueError("本地工作区不能是符号链接。")
        root.mkdir(exist_ok=True, mode=0o700)
        resources = [source / "tools/build_magazine.py"]
        resources.extend(path for path in (source / "web").rglob("*") if path.is_file())
        resources.extend(source / name for name in ("README.md", "LICENSE", "NOTICE.md", "数据来源.md", "补档说明.md"))
        changed = False
        for file in resources:
            if not file.exists():
                continue
            relative = file.relative_to(source)
            target = root / relative
            if file.is_symlink() or any(parent.is_symlink() for parent in (target, *target.parents) if parent == root or root in parent.parents):
                raise ValueError("本地应用资源不能使用符号链接。")
            content = file.read_bytes()
            if not target.exists() or target.read_bytes() != content:
                target.parent.mkdir(parents=True, exist_ok=True)
                # 图标等二进制资源也使用同目录临时文件再替换。
                import tempfile
                descriptor, temporary = tempfile.mkstemp(prefix=".resource-", dir=target.parent)
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(content)
                    os.replace(temporary, target)
                finally:
                    Path(temporary).unlink(missing_ok=True)
                changed = True
        if changed or not (root / "dist/index.html").is_file():
            build_site(root, allow_empty=True)
        return root
    finally:
        lock.release()
