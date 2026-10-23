"""云端真实验收：空白采编、幂等重跑、隔离分支回写和安全摘要。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from . import models, pipeline, sources
from .build import build_site
from .config import REPOSITORY, load_config
from .local import prepare_local_workspace
from .privacy import check_changes, scan_paths

REQUIRED = ("ai", "daily", "daily_editorial", "daily_archives", "build")
SUMMARY = "verification.json"
MAX_FILES = 1200
MAX_BYTES = 64 * 1024 * 1024


class VerificationError(ValueError):
    """只包含固定中文说明，不含模型配置、响应或执行日志。"""


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@contextmanager
def _environment(**values):
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@contextmanager
def _count_calls():
    """仅计数并转发真实函数；不替换返回值，也不保留请求或响应。"""
    counts = {"model_requests": 0, "source_requests": 0}
    real_model, real_source = models._request, sources._download_once

    def model(*args, **kwargs):
        counts["model_requests"] += 1
        return real_model(*args, **kwargs)

    def source(*args, **kwargs):
        counts["source_requests"] += 1
        return real_source(*args, **kwargs)

    models._request, sources._download_once = model, source
    try:
        yield counts
    finally:
        models._request, sources._download_once = real_model, real_source


def _same_day(day) -> None:
    if pipeline._today() != day:
        raise VerificationError("验证跨越北京时间午夜，请在新的一天重新运行；未将当前榜单伪装成旧日期。")


def _validate_first(state: dict, counts: dict, day) -> None:
    tasks = state.get("tasks", {})
    required = REQUIRED + (("weekly", "weekly_editorial", "weekly_archives") if day.weekday() == 0 else ())
    if any(tasks.get(name, {}).get("status") != "success" for name in required):
        raise VerificationError("真实采编未全部通过：AI 资讯、项目介绍、档案和页面必须成功；跳过或降级不算验收成功。")
    if counts["model_requests"] < 2 or counts["source_requests"] < 1:
        raise VerificationError("未观察到真实来源抓取和至少两次模型请求，不能认定云端采编已跑通。")
    if any(tasks[name].get("count", 0) < 1 for name in ("ai", "daily", "daily_archives")):
        raise VerificationError("真实采编返回空内容，不能认定验收成功。")
    for name, task in tasks.items():
        # 从空白开始没有上月历史，不能用新抓取资料伪造月报。
        empty_month = (name == "monthly" and day.day == 1 and task.get("status") == "failed"
                       and task.get("reason") == "上月无可解析日报，未生成空月榜")
        if task.get("status") == "failed" and not empty_month:
            raise VerificationError("有采编子任务失败，不能认定验收成功。")


def _content_files(root: Path) -> dict[str, str]:
    """输入根仅为本次空白刊物；拒绝隐藏路径、链接和白名单外文件。"""
    files = {}
    for directory in ("GitHub项目分析", "AI前沿资讯/日报", "dist"):
        base = root / directory
        if base.is_symlink():
            raise VerificationError("验收产物不能包含符号链接。")
        for path in sorted(base.rglob("*")):
            if path.is_symlink():
                raise VerificationError("验收产物不能包含符号链接。")
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                if any(part.startswith(".") for part in PurePosixPath(relative).parts) or check_changes(root, [relative]):
                    raise VerificationError("验收产物包含白名单外路径。")
                files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ("tools/_杂志数据.json", "content-manifest.json"):
        path = root / name
        if path.is_symlink():
            raise VerificationError("验收产物不能包含符号链接。")
        if path.is_file():
            files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if len(files) > MAX_FILES or sum((root / name).stat().st_size for name in files) > MAX_BYTES:
        raise VerificationError("验收产物超过数量或大小上限。")
    return files


def _validate_repeat(first: dict[str, str], second: dict[str, str], state: dict, counts: dict, day) -> None:
    if counts["model_requests"] or counts["source_requests"] or first != second:
        raise VerificationError("重复运行新增了网络调用或修改了刊物、档案，幂等验收失败。")
    tasks = state.get("tasks", {})
    if any(tasks.get(name, {}).get("status") != "skipped" for name in ("ai", "daily", "build")):
        raise VerificationError("第二次运行未复用已有有效内容，幂等验收失败。")
    for name in ("daily_archives", "weekly_archives"):
        if name == "weekly_archives" and day.weekday() != 0:
            continue
        task = tasks.get(name, {})
        if task.get("status") != "success" or task.get("added") or task.get("updated") or task.get("changed"):
            raise VerificationError("第二次运行重复归档或修改了上榜记录。")
    for name, task in tasks.items():
        if task.get("status") == "failed" and not (
            name == "monthly" and day.day == 1 and task.get("reason") == "上月无可解析日报，未生成空月榜"
        ):
            raise VerificationError("第二次运行有未完成的采编任务。")


def generate(source: Path, output: Path) -> dict:
    source = source.resolve()
    if output.is_symlink() or any(parent.is_symlink() for parent in output.parents):
        raise VerificationError("验收输出目录不能使用符号链接。")
    output = output.resolve()
    if output == source or source in output.parents or (output.exists() and any(output.iterdir())):
        raise VerificationError("验收输出须使用源码目录外的全新空目录。")
    output.mkdir(parents=True, exist_ok=True)
    day = pipeline._today()
    result = {"schema": 1, "ok": False, "date": day.isoformat(), "mode": "real-cloud-validation"}
    _write(output / SUMMARY, result)
    try:
        with tempfile.TemporaryDirectory(prefix="daily-cloud-check-") as directory:
            temporary = Path(directory)
            with _environment(GH_DAILY_DATA_DIR=str(temporary / "data"), GH_DAILY_CONFIG_DIR=str(temporary / "config")):
                required_env = ("GH_DAILY_BASE_URL", "GH_DAILY_MODEL", "GH_DAILY_API_KEY")
                if any(not os.environ.get(key, "").strip() for key in required_env):
                    raise VerificationError("请在 Actions Secrets 配置 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL 三项；未发起模型请求。")
                settings = load_config()
                if settings["provider"] != "cloud":
                    raise VerificationError("GitHub 云端验收仅支持公开 HTTPS 兼容模型接口。")
                root = prepare_local_workspace(source)
                with _count_calls() as first_calls:
                    first = pipeline.run_update(root)
                _same_day(day)
                result["first_tasks"] = {name: task.get("status") for name, task in first.get("tasks", {}).items()}
                result["first_calls"] = dict(first_calls)
                _validate_first(first, first_calls, day)
                database = json.loads((root / "tools/_杂志数据.json").read_text(encoding="utf-8"))
                daily = [issue for issue in database["issues"] if issue["type"] == "daily"]
                if len(daily) != 1 or daily[0]["issue"] != 1 or daily[0]["date"] != day.isoformat():
                    raise VerificationError("空白工作区未生成当天的第 001 期。")
                before = _content_files(root)
                with _count_calls() as repeat_calls:
                    repeat = pipeline.run_update(root)
                _same_day(day)
                _validate_repeat(before, _content_files(root), repeat, repeat_calls, day)
                result.update(repeat_calls=dict(repeat_calls), idempotent=True, first_issue=1,
                              ai_articles=first["tasks"]["ai"]["count"], projects=first["tasks"]["daily"]["count"],
                              monthly="not_applicable_without_history" if day.day == 1 else "not_due")
                # 导出只读页面，排除本地设置入口及所有运行日志、配置、原始响应。
                build_site(root, hosted=True)
                shutil.copyfile(root / "dist/content-manifest.json", root / "content-manifest.json")
                files = _content_files(root)
                if scan_paths(root, public_release=True):
                    raise VerificationError("验收产物未通过隐私检查，未上传原始响应或运行日志。")
                for name in files:
                    content = (root / name).read_bytes()
                    if settings["api_key"].encode() in content or settings["base_url"].encode() in content:
                        raise VerificationError("验收产物出现模型配置内容，已停止导出。")
                for name in files:
                    target = output / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(root / name, target)
                result.update(generation_ok=True, files=files, writeback="pending")
    except Exception as exc:
        # 失败只上传固定说明及状态枚举，不暴露异常细节和私人配置。
        result["message"] = str(exc) if isinstance(exc, VerificationError) else "云端采编验收未完成；请检查配置、可用额度和来源可达性。"
        _write(output / SUMMARY, result)
        raise VerificationError(result["message"]) from None
    _write(output / SUMMARY, result)
    return result


def _identity() -> tuple[str, str]:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    run, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    if not REPOSITORY.fullmatch(repository) or not re.fullmatch(r"[0-9]{1,20}", run) or not re.fullmatch(r"[0-9]{1,10}", attempt):
        raise VerificationError("回写验证只接受 GitHub 提供的仓库和运行标识。")
    return f"https://github.com/{repository}.git", f"refs/heads/cloud-validation/{run}-{attempt}"


def _git(root: Path, *arguments: str) -> str:
    command = ["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
               "-c", "http.proxy=", "-c", "https.proxy=", *arguments]
    try:
        process = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8",
                                 timeout=120, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except (OSError, subprocess.TimeoutExpired):
        raise VerificationError("验证分支网络操作超时或无法执行，未输出凭据或原始日志。") from None
    if process.returncode:
        raise VerificationError("验证分支操作失败，请检查仓库写权限和分支保护；未输出凭据或原始日志。")
    return process.stdout.strip()


def cleanup(state_path: Path) -> None:
    if not state_path.exists():
        return
    url, ref = _identity()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    commit = state.get("commit", "")
    if state.get("ref") != ref or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise VerificationError("清理状态不匹配当前工作流，拒绝删除分支。")
    head = _git(state_path.parent, "ls-remote", "--heads", url, ref)
    if head and head.split()[0] != commit:
        raise VerificationError("验证分支已被其它操作修改，拒绝删除。")
    if head:
        with tempfile.TemporaryDirectory(prefix="daily-cloud-cleanup-") as directory:
            temporary = Path(directory)
            _git(temporary, "init", "--quiet")
            _git(temporary, "push", f"--force-with-lease={ref}:{commit}", url, f":{ref}")
        if _git(state_path.parent, "ls-remote", "--heads", url, ref):
            raise VerificationError("验证分支清理未获远端确认。")
    state_path.unlink()


def writeback(output: Path, state_path: Path) -> dict:
    url, ref = _identity()
    result = json.loads((output / SUMMARY).read_text(encoding="utf-8"))
    files = result.get("files", {})
    if result.get("generation_ok") is not True or not isinstance(files, dict) or not files or len(files) > MAX_FILES:
        raise VerificationError("只有完整通过真实采编和幂等验收的产物可以验证回写。")
    if any(not isinstance(name, str) or any(part.startswith(".") for part in PurePosixPath(name).parts)
           or check_changes(output, [name]) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
           for name, digest in files.items()):
        raise VerificationError("回写清单含不安全路径或校验值。")
    if scan_paths(output, site_release=True):
        raise VerificationError("回写产物未通过隐私检查。")
    if sum((output / name).stat().st_size for name in files) > MAX_BYTES:
        raise VerificationError("回写产物超过大小上限。")
    if _git(output, "ls-remote", "--heads", url, ref):
        raise VerificationError("本次验证分支已存在，拒绝覆盖。")
    with tempfile.TemporaryDirectory(prefix="daily-cloud-push-") as directory:
        repository = Path(directory) / "stage"
        repository.mkdir()
        for name, digest in files.items():
            path = output / name
            if not path.is_file() or path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
                raise VerificationError("回写文件丢失或使用了符号链接。")
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise VerificationError("回写前文件校验失败。")
            target = repository / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        shutil.copyfile(output / SUMMARY, repository / SUMMARY)
        summary_hash = hashlib.sha256((repository / SUMMARY).read_bytes()).hexdigest()
        _git(repository, "init", "--quiet")
        _git(repository, "add", "--", ".")
        _git(repository, "-c", "user.name=GitHub Daily Press", "-c", "user.email=maintainer@example.invalid",
             "commit", "--quiet", "-m", "验证云端采编的公开产物回写")
        commit = _git(repository, "rev-parse", "HEAD")
        _write(state_path, {"ref": ref, "commit": commit})
        try:
            # 空 lease 要求远端不存在，绝不覆盖任何已存在分支。
            _git(repository, "push", f"--force-with-lease={ref}:", url, f"HEAD:{ref}")
            audit = Path(directory) / "readback"
            audit.mkdir()
            _git(audit, "init", "--quiet")
            _git(audit, "fetch", "--quiet", "--depth=1", url, ref)
            if _git(audit, "rev-parse", "FETCH_HEAD") != commit:
                raise VerificationError("远端读回的提交与本次验证不一致。")
            _git(audit, "checkout", "--quiet", "--detach", "FETCH_HEAD")
            for name, digest in files.items():
                if hashlib.sha256((audit / name).read_bytes()).hexdigest() != digest:
                    raise VerificationError("远端读回文件的校验值不一致。")
            if hashlib.sha256((audit / SUMMARY).read_bytes()).hexdigest() != summary_hash:
                raise VerificationError("远端读回的验收摘要校验失败。")
        finally:
            cleanup(state_path)
    result.update(ok=True, writeback="verified_and_branch_deleted")
    _write(output / SUMMARY, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="云端真实采编验收")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("generate")
    collect.add_argument("--source", type=Path, required=True)
    collect.add_argument("--output", type=Path, required=True)
    push = commands.add_parser("writeback")
    push.add_argument("--output", type=Path, required=True)
    push.add_argument("--state", type=Path, required=True)
    remove = commands.add_parser("cleanup")
    remove.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            result = generate(args.source, args.output)
            print(f"真实采编和幂等验收通过：AI 资讯 {result['ai_articles']} 条，项目 {result['projects']} 个；待验证远端回写。")
        elif args.command == "writeback":
            writeback(args.output, args.state)
            print("云端真实采编、远端逐文件读回、临时分支删除全部通过。生产定时开关未改变。")
        else:
            cleanup(args.state)
            print("本次验证分支清理检查完成。")
        return 0
    except Exception as exc:
        message = str(exc) if isinstance(exc, VerificationError) else "云端验收未完成；原始错误与配置不输出到日志。"
        if args.command == "writeback":
            try:
                result = json.loads((args.output / SUMMARY).read_text(encoding="utf-8"))
                result.update(ok=False, writeback="failed", message=message)
                _write(args.output / SUMMARY, result)
            except (OSError, ValueError):
                pass
        print(message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
