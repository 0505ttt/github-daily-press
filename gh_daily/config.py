"""用户配置：仅保存于站点目录之外，公开读取永不包含密钥。"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

DEFAULTS = {
    "provider": "cloud", "base_url": "https://api.openai.com/v1",
    "api_key": "", "model": "", "timeout": 45, "max_tokens": 4096,
    "source_repo": "",
}
ENVIRONMENT = {
    "provider": "GH_DAILY_PROVIDER", "base_url": "GH_DAILY_BASE_URL",
    "api_key": "GH_DAILY_API_KEY", "model": "GH_DAILY_MODEL",
    "source_repo": "GH_DAILY_SOURCE_REPO",
}
REPOSITORY = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9_.-]{1,100}\Z")


class ConfigError(ValueError):
    """可安全展示的配置错误。"""


def config_directory() -> Path:
    configured = os.environ.get("GH_DAILY_CONFIG_DIR")
    if configured:
        return Path(configured).expanduser().absolute()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "gh-daily"
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "gh-daily"


def _normalized_url(value: str, provider: str) -> str:
    url = urlsplit(value.strip())
    try:
        host = url.hostname.encode("idna").decode("ascii").lower()
        port = url.port
    except (AttributeError, UnicodeError, ValueError):
        raise ConfigError("API URL 格式不正确。") from None
    if ":" in host:
        host = "[" + host + "]"
    authority = host + (":11434" if provider == "ollama" else (":" + str(port) if port not in {None, 443} else ""))
    return urlunsplit((url.scheme.lower(), authority, url.path.rstrip("/"), "", ""))


def prepare_config(patch: dict, base: dict | None = None) -> dict:
    if not isinstance(patch, dict) or set(patch) - (set(DEFAULTS) | {"clear_api_key"}):
        raise ConfigError("配置字段不正确。")
    result = dict(DEFAULTS if base is None else base)
    for key, value in patch.items():
        if key == "clear_api_key":
            if not isinstance(value, bool):
                raise ConfigError("清除密钥选项不正确。")
        elif key == "api_key" and isinstance(value, str) and not value.strip():
            continue
        else:
            result[key] = value
    if patch.get("clear_api_key"):
        result["api_key"] = ""
    for key in ("provider", "base_url", "api_key", "model", "source_repo"):
        if not isinstance(result.get(key), str):
            raise ConfigError("配置内容必须是文字。")
        result[key] = result[key].strip()
    if result["provider"] not in {"cloud", "ollama"}:
        raise ConfigError("请选择云端兼容接口或 Ollama。")
    for key, minimum, maximum in (("timeout", 3, 120), ("max_tokens", 16, 16384)):
        if type(result.get(key)) is not int or not minimum <= result[key] <= maximum:
            raise ConfigError("超时须为 3—120 秒，输出上限须为 16—16384。")
    if len(result["model"]) > 200 or len(result["api_key"]) > 4096:
        raise ConfigError("模型名称或密钥过长。")
    if any(ord(ch) < 32 for value in result.values() if isinstance(value, str) for ch in value):
        raise ConfigError("配置中不能含有控制字符。")
    if result["source_repo"] and not REPOSITORY.fullmatch(result["source_repo"]):
        raise ConfigError("仓库请填写 owner/repo，例如 example/gh-daily。")
    try:
        url = urlsplit(result["base_url"])
        port = url.port
    except ValueError:
        raise ConfigError("API URL 格式不正确。") from None
    if (not url.hostname or url.username or url.password or url.query or url.fragment
            or len(result["base_url"]) > 2048 or "\\" in result["base_url"]
            or any(part in {".", ".."} for part in url.path.split("/"))):
        raise ConfigError("API URL 不能含账号、查询参数或路径跳转。")
    if result["provider"] == "cloud":
        if url.scheme != "https" or (port is not None and port != 443):
            raise ConfigError("云端 API 必须使用 HTTPS 默认端口。")
    elif (url.scheme != "http" or url.hostname not in {"localhost", "127.0.0.1", "::1"}
          or port not in {None, 11434} or url.path.rstrip("/") not in {"", "/api"}):
        raise ConfigError("Ollama 仅支持本机 http://127.0.0.1:11434。")
    result["base_url"] = _normalized_url(result["base_url"], result["provider"])
    if base is not None:
        previous_endpoint = (base["provider"], _normalized_url(base["base_url"], base["provider"]))
        current_endpoint = (result["provider"], result["base_url"])
        supplied_key = patch.get("api_key")
        has_new_key = isinstance(supplied_key, str) and bool(supplied_key.strip())
        if current_endpoint != previous_endpoint and not has_new_key:
            result["api_key"] = ""
    return {key: result[key] for key in DEFAULTS}


def _stored_config() -> dict:
    path = config_directory() / "config.json"
    if path.is_symlink():
        raise ConfigError("配置文件不能是符号链接。")
    if not path.exists():
        return dict(DEFAULTS)
    try:
        if path.stat().st_size > 16384:
            raise ConfigError("配置文件过大。")
        data = json.loads(path.read_text(encoding="utf-8"))
        return prepare_config(data)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ConfigError("无法读取配置，请检查用户配置目录。") from None


def load_config() -> dict:
    stored = _stored_config()
    override = {key: os.environ[environment] for key, environment in ENVIRONMENT.items()
                if environment in os.environ}
    return prepare_config(override, stored)


def public_config() -> dict:
    result = load_config()
    key_set = bool(result.pop("api_key"))
    return {**result, "api_key_set": key_set,
            "environment_fields": [key for key, env in ENVIRONMENT.items() if env in os.environ]}


def save_config(patch: dict) -> dict:
    stored = _stored_config()
    result = prepare_config(patch, stored)
    if os.environ.get("GH_DAILY_API_KEY", "").strip():
        current = load_config()
        requested = prepare_config(patch, current)
        if (requested["provider"], requested["base_url"]) != (current["provider"], current["base_url"]):
            raise ConfigError("当前密钥由环境变量提供；更换接口请同时修改环境变量中的接口地址、类型和密钥。")
    directory = config_directory()
    if directory.is_symlink():
        raise ConfigError("配置目录不能是符号链接。")
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(directory, 0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".config-", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            os.chmod(temporary, 0o600)
            json.dump(result, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, directory / "config.json")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return public_config()
