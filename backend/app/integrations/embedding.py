"""DashScope Embedding（OpenAI 兼容模式）。

只负责「文本 → 向量」，切分与入库由 services/ingest_service 编排。
"""

import json
import logging
import urllib.error
import urllib.request

from app.core.config import settings_cache
from app.core.errors import api_error

logger = logging.getLogger("yunshu.embedding")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

# 单次请求条数：官方限制 25，取 10 更稳（失败重试代价小）
BATCH_SIZE = 10


def _request(api_key: str, url: str, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def embed_texts(texts: list[str], timeout: int = 30) -> list[list[float]]:
    """批量向量化，返回与输入等长的向量列表。失败统一抛 10008。"""
    if not texts:
        return []

    if not settings_cache.dashscope_api_key:
        raise api_error(10008, "向量化服务未配置，请联系管理员", 503)

    url = f"{settings_cache.embedding_base_url.rstrip('/')}/embeddings"
    vectors: list[list[float]] = []

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        payload = {"model": settings_cache.embedding_model, "input": batch}
        try:
            body = _request(settings_cache.dashscope_api_key, url, payload, timeout)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "ignore")[:300]
            logger.warning("向量化失败：HTTP %s %s", exc.code, detail)
            raise api_error(10008, "文档向量化失败，请稍后重试", 503)
        except Exception as exc:
            logger.warning("向量化异常：%s", type(exc).__name__)
            raise api_error(10008, "文档向量化失败，请稍后重试", 503)

        rows = body.get("data") or []
        if len(rows) != len(batch):
            logger.warning("向量化返回条数不符：期望 %s 实际 %s", len(batch), len(rows))
            raise api_error(10008, "文档向量化返回异常", 503)
        vectors.extend(item["embedding"] for item in rows)

    return vectors
