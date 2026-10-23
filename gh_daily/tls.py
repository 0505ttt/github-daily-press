"""保留系统信任设置，并补充跨平台公开 CA；从不关闭证书校验。"""
import ssl

import certifi


def verified_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context
