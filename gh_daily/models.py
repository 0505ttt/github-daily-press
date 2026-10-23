"""有界模型请求。禁用重定向与代理，并将 DNS 检查结果固定到连接。"""

from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import ssl
from urllib.parse import urlsplit

from .config import load_config, prepare_config
from .tls import verified_context

MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class ModelError(ValueError):
    """对外只展示固定错误，不透出服务端响应或密钥。"""


class FormatUnsupported(ModelError):
    pass


def _addresses(host: str, port: int, local: bool = False) -> list[str]:
    try:
        answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addresses = list(dict.fromkeys(answer[4][0] for answer in answers))
    except OSError:
        raise ModelError("API 主机解析失败，请检查地址和网络。") from None
    if not addresses:
        raise ModelError("API 主机没有可用地址。")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if (local and not ip.is_loopback) or (not local and not ip.is_global):
            raise ModelError("API 地址不在允许的网络范围内。")
    return addresses


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, port: int, timeout: int):
        super().__init__(host, port=port, timeout=timeout, context=verified_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


def _request(config: dict, payload: dict) -> dict:
    url = urlsplit(config["base_url"])
    local = config["provider"] == "ollama"
    port = url.port or (11434 if local else 443)
    address = _addresses(url.hostname, port, local=local)[0]
    prefix = url.path.rstrip("/")
    if local:
        path = (prefix if prefix.endswith("/api") else prefix + "/api") + "/chat"
        connection = http.client.HTTPConnection(address, port, timeout=config["timeout"])
    else:
        path = prefix + "/chat/completions"
        connection = _PinnedHTTPS(url.hostname, address, port, config["timeout"])
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if not local and config["api_key"]:
        headers["Authorization"] = "Bearer " + config["api_key"]
    try:
        connection.request("POST", path, json.dumps(payload).encode("utf-8"), headers)
        response = connection.getresponse()
        if response.status in {400, 404, 422} and ("response_format" in payload or "format" in payload):
            raise FormatUnsupported("此接口不支持当前结构化输出格式。")
        if 300 <= response.status < 400:
            raise ModelError("API 返回重定向，已停止请求，请使用最终 API 地址。")
        if not 200 <= response.status < 300:
            if response.status in {401, 403}:
                raise ModelError("API 鉴权失败，请检查密钥和模型权限。")
            if response.status == 429:
                raise ModelError("API 请求受限，请检查额度并稍后重试。")
            raise ModelError("API 请求失败，请检查接口、模型和服务状态。")
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ModelError("API 响应超过安全大小上限。")
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ModelError("API 响应格式不正确。")
        return data
    except (socket.timeout, TimeoutError):
        raise ModelError("API 请求超时。") from None
    except (OSError, ssl.SSLError, http.client.HTTPException):
        raise ModelError("API 连接失败，请检查网络或本机 Ollama 服务。") from None
    except (json.JSONDecodeError, UnicodeError):
        raise ModelError("API 返回了无法解析的响应。") from None
    finally:
        connection.close()


def _validate(value, schema: dict, depth: int = 0) -> None:
    if depth > 30:
        raise ModelError("模型输出层级过深。")
    kinds = {"object": dict, "array": list, "string": str, "number": (int, float),
             "integer": int, "boolean": bool, "null": type(None)}
    kind = schema.get("type")
    choices = kind if isinstance(kind, list) else [kind] if kind else []
    if choices and not any(isinstance(value, kinds.get(item, type(None)))
                           and not (item in {"number", "integer"} and isinstance(value, bool))
                           for item in choices):
        raise ModelError("模型输出字段类型不符合要求。")
    if "enum" in schema and value not in schema["enum"]:
        raise ModelError("模型输出包含不允许的值。")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        if set(schema.get("required", [])) - set(value):
            raise ModelError("模型输出缺少必要字段。")
        if schema.get("additionalProperties") is False and set(value) - set(props):
            raise ModelError("模型输出包含多余字段。")
        for key, item in value.items():
            if key in props:
                _validate(item, props[key], depth + 1)
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", 10000):
            raise ModelError("模型输出条目数量不符合要求。")
        for item in value:
            _validate(item, schema.get("items", {}), depth + 1)
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 1000000):
            raise ModelError("模型输出文字长度不符合要求。")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < schema.get("minimum", float("-inf")) or value > schema.get("maximum", float("inf")):
            raise ModelError("模型输出数值不符合要求。")


def generate_json(prompt: str, schema: dict, config: dict | None = None) -> dict:
    settings = prepare_config(config if config is not None else load_config())
    if not settings["model"]:
        raise ModelError("请先配置模型名称。")
    if settings["provider"] == "cloud" and not settings["api_key"]:
        raise ModelError("请先配置 API Key。")
    if not isinstance(prompt, str) or len(prompt) > 500000 or not isinstance(schema, dict):
        raise ModelError("模型输入不正确或过大。")
    messages = [{"role": "system", "content": "你是中文资讯编辑。只返回符合指定 JSON Schema 的 JSON 对象，不使用 Markdown 代码块。"},
                {"role": "user", "content": prompt + "\nJSON Schema：" + json.dumps(schema, ensure_ascii=False)}]
    mode, invalid_retries, requests = 0, 0, 0
    # 最多两次格式降级与一次无效输出重试，四次请求覆盖完整兼容路径。
    while requests < 4:
        local = settings["provider"] == "ollama"
        payload = {"model": settings["model"], "messages": messages, "stream": False}
        if local:
            payload["options"] = {"num_predict": settings["max_tokens"]}
            if mode < 2:
                payload["format"] = schema if mode == 0 else "json"
        else:
            payload["max_tokens"] = settings["max_tokens"]
            if mode < 2:
                payload["response_format"] = ({"type": "json_schema", "json_schema": {
                    "name": "gh_daily_response", "strict": True, "schema": schema}}
                    if mode == 0 else {"type": "json_object"})
        try:
            requests += 1
            response = _request(settings, payload)
        except FormatUnsupported:
            if mode >= 2:
                raise ModelError("此接口的结构化输出测试未通过，请检查兼容性。") from None
            mode += 1
            continue
        try:
            content = response["message"]["content"] if local else response["choices"][0]["message"]["content"]
            output = json.loads(content)
            if not isinstance(output, dict):
                raise ModelError("模型必须返回 JSON 对象。")
            _validate(output, schema)
            return output
        except (KeyError, IndexError, TypeError, ValueError):
            if invalid_retries:
                raise ModelError("模型输出校验失败，已重试一次；原有内容保持有效。") from None
            invalid_retries += 1
    raise ModelError("此接口的结构化输出测试未通过，请检查兼容性。")


def test_connection(config: dict | None = None) -> dict:
    settings = prepare_config(config if config is not None else load_config())
    settings["max_tokens"] = 64
    result = generate_json("请返回 {\"ok\":true}。", {
        "type": "object", "properties": {"ok": {"type": "boolean", "enum": [True]}},
        "required": ["ok"], "additionalProperties": False,
    }, settings)
    return {"ok": result["ok"], "message": "连接成功，JSON 输出校验通过。"}
