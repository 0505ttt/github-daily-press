"""中文命令行入口。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="GitHub 每日项目推送 · 本地应用与采编")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent, help="公开版项目目录")
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("serve", help="启动本地阅读应用")
    start.add_argument("--open", action="store_true", help="首次安装时打开浏览器")
    start.add_argument("--schedule", action="store_true", help="同时启用本地每日采编")
    update = sub.add_parser("update", help="采集并生成日报，周一/月初自动增加对应报告")
    update.add_argument("--date", help="目标日期；在线抓取仅允许今天")
    update.add_argument("--force", action="store_true", help="重新生成当天内容")
    sub.add_parser("build", help="从已保存的公开历史重新构建")
    sync = sub.add_parser("sync", help="同步自己公开仓库的阅读内容")
    sync.add_argument("--repo", help="owner/repository")
    sub.add_parser("doctor", help="检查依赖、模型配置及公开构建")
    sub.add_parser("privacy", help="扫描公开版的隐私风险")
    sub.add_parser("check-changes", help="验证云端待提交文件白名单")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "serve":
            from .build import build_site
            from .server import serve
            if not (root / "dist/index.html").exists():
                build_site(root)
            serve(root, port=8765, open_browser=args.open, schedule=args.schedule)
            return 0
        if args.command == "build":
            from .build import build_site
            result = build_site(root)
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
