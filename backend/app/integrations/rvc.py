"""RVC 变声：把音频转发给本地 RVC 微服务（独立 Python 3.11 进程）。

后端本身不装 torch / fairseq，避免污染主环境（3.14 也装不上）。
微服务不可用时返回 None，业务层降级为「用 TTS 原声」，不阻断面试。
"""

import json
import logging
import urllib.error
import urllib.request

from app.core.config import settings_cache

logger = logging.getLogger("yunshu.rvc")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def convert(wav_bytes: bytes, timeout: int | None = None) -> bytes | None:
    """把 WAV 送去变声，返回 WAV 字节；关闭或失败时返回 None。"""
    if not settings_cache.rvc_enabled or not wav_bytes:
        return None

    url = f"{settings_cache.rvc_service_url.rstrip('/')}/convert"
    request = urllib.request.Request(url, data=wav_bytes, method="POST")
    request.add_header("Content-Type", "audio/wav")

    try:
        with urllib.request.urlopen(
            request, timeout=timeout or settings_cache.rvc_timeout_seconds
        ) as response:
            data = response.read()
            return data or None
    except urllib.error.URLError as exc:
        logger.warning("RVC 微服务不可用：%s", exc)
        return None
    except Exception as exc:
        logger.warning("RVC 变声失败：%s", type(exc).__name__)
        return None


def healthy() -> dict:
    """自检用：返回微服务健康状态与模型信息。"""
    url = f"{settings_cache.rvc_service_url.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}
