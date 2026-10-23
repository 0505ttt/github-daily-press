"""中文命令行入口。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    # 命令结果也会由脚本、Actions 和启动器读取，统一为 UTF-8，避免 Windows
    # 重定向输出时沿用 cp1252 等本地编码而无法输出中文。
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="GitHub 每日项目推送 · 本地应用与采编")
    parser.add_argument("--root", type=Path, help="显式选择采编目录；本地启动默认使用独立空白工作区")
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("serve", help="启动本地阅读应用")
    start.add_argument("--open", action="store_true", help="首次安装时打开浏览器")
    start.add_argument("--schedule", action="store_true", help="同时启用本地每日采编")
    update = sub.add_parser("update", help="采集并生成日报，周一/月初自动增加对应报告")
    update.add_argument("--date", help="目标日期；在线抓取仅允许今天")
    update.add_argument("--force", action="store_true", help="重新生成当天内容")
    build = sub.add_parser("build", help="从已保存的公开历史重新构建")
    build.add_argument("--hosted", action="store_true", help="构建无本机设置接口的在线阅读版")
    build.add_argument("--base-path", default="/", help="在线站点路径，如 /github-daily-press/")
    content_import = sub.add_parser("import-content", help="从既有 AI 采编目录安全导入报告和分类档案")
    content_import.add_argument("--source", type=Path, required=True, help="含 GitHub项目分析/ 与 AI前沿资讯/ 的目录")
    sub.add_parser("publish", help="校验后只提交并推送白名单阅读产物")
    sub.add_parser("workspace", help="显示自己的本地采编目录，可交给已有 AI 工具管理")
    sync = sub.add_parser("sync", help="同步自己公开仓库的阅读内容")
    sync.add_argument("--repo", help="owner/repository")
    sub.add_parser("doctor", help="检查依赖、模型配置及公开构建")
    sub.add_parser("privacy", help="扫描公开版的隐私风险")
    sub.add_parser("check-changes", help="验证云端待提交文件白名单")
    args = parser.parse_args(argv)
    result: dict[str, object]
    try:
        source_root = Path(__file__).resolve().parent.parent
        root = args.root.resolve() if args.root is not None else source_root
        if args.root is None and args.command in {"serve", "update", "sync", "doctor", "workspace"}:
            from .local import prepare_local_workspace
            root = prepare_local_workspace(source_root)
        if args.command == "workspace":
            result = {"status": "success", "workspace": str(root), "message": "本地刊物从空白开始，第一次成功生成的日报为第 001 期；重启不重置。"}
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "serve":
            from .build import build_site
            from .server import serve
            if not (root / "dist/index.html").exists():
                build_site(root)
            serve(root, port=8765, open_browser=args.open, schedule=args.schedule)
            return 0
        if args.command == "build":
            from .build import build_site
            result = build_site(root, hosted=args.hosted, base_path=args.base_path)
        elif args.command == "import-content":
            from .publishing import import_content
            result = import_content(root, args.source)
        elif args.command == "publish":
            from .publishing import publish_content
            result = publish_content(root)
        elif args.command == "update":
            from .pipeline import run_update
            result = run_update(root, date_str=args.date, force=args.force)
        elif args.command == "sync":
            from .sync import sync_content
            result = sync_content(root, repo=args.repo)
        elif args.command == "privacy":
            from .privacy import scan_paths
            findings = scan_paths(root, public_release=True)
            result = {"status": "failed" if findings else "success", "findings": findings}
        elif args.command == "check-changes":
            import subprocess
            from .privacy import check_changes, scan_paths
            changed = subprocess.check_output(["git", "diff", "--name-only", "-z", "HEAD"], cwd=root).decode().split("\0")
            untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root).decode().split("\0")
            bad = check_changes(root, [p for p in changed + untracked if p])
            findings = scan_paths(root, public_release=True)
            result = {"status": "failed" if bad or findings else "success", "unexpected": bad, "findings": findings}
        else:
            from .config import public_config
            from .privacy import scan_paths
            import requests
            import bs4
            site_exists = (root / "dist/index.html").exists()
            privacy_count = len(scan_paths(root, public_release=True))
            result = {"status": "success" if site_exists and not privacy_count else "failed", "Python": sys.version.split()[0], "模型设置": public_config(), "静态站点": site_exists, "隐私问题数": privacy_count}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("status") in {"failed", "partial", "error"} else 0
    except KeyboardInterrupt:
        print("已停止。")
        return 0
    except Exception as error:
        # 模型、网络模块必须提供脱敏异常；这里仍不输出请求、配置或堆栈。
        print("操作未完成：" + str(error), file=sys.stderr)
        return 1
