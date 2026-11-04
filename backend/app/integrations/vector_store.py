"""Milvus 向量库适配：建集合、写入切片、按 doc_id 删除、相似度检索。

集合结构（面试资料与简历各一个集合，字段一致）：
    id          主键（doc_id-chunk_index）
    doc_id      来源文档 id
    chunk_index 片序号
    title       所属小节标题（检索结果里作为来源提示）
    content     切片正文
    vector      稠密向量（COSINE）

连接按进程复用；集合在首次使用时按需创建。
"""

import logging
import warnings

# pymilvus 3.x 把 ORM 风格 API 标为废弃（3.1 移除），但功能正常。
# requirements 已锁 3.0.2，这里压掉刷屏警告；将来升级到 3.1 需改用 MilvusClient。
warnings.filterwarnings("ignore", message=".*ORM-style PyMilvus API.*")

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from app.core.config import settings_cache
from app.core.errors import api_error

logger = logging.getLogger("yunshu.milvus")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

_connected = False
CONTENT_MAX = 8192
TITLE_MAX = 256


def _truncate_bytes(text: str, max_bytes: int) -> str:
    """Milvus 的 VARCHAR 长度按字节算，中文一个字 3 字节，必须按字节截断。"""
    data = (text or "").encode("utf-8")
    if len(data) <= max_bytes:
        return text or ""
    return data[:max_bytes].decode("utf-8", "ignore")


def _ensure_connection() -> None:
    global _connected
    if _connected:
        return
    try:
        connections.connect(
            alias="default",
            host=settings_cache.milvus_host,
            port=str(settings_cache.milvus_port),
            timeout=10,
        )
        _connected = True
    except Exception as exc:
        logger.warning("Milvus 连接失败：%s", type(exc).__name__)
        raise api_error(10008, "向量库暂不可用，请稍后重试", 503)


def ensure_collection(name: str, dim: int | None = None) -> Collection:
    """集合不存在则创建并建索引；已存在直接返回。"""
    _ensure_connection()
    if utility.has_collection(name):
        return Collection(name)

    dimension = dim or settings_cache.embedding_dim
    fields = [
        FieldSchema("id", DataType.VARCHAR, is_primary=True, max_length=64),
        FieldSchema("doc_id", DataType.INT64),
        FieldSchema("chunk_index", DataType.INT64),
        FieldSchema("title", DataType.VARCHAR, max_length=TITLE_MAX),
        FieldSchema("content", DataType.VARCHAR, max_length=CONTENT_MAX),
        FieldSchema("vector", DataType.FLOAT_VECTOR, dim=dimension),
    ]
    collection = Collection(name, CollectionSchema(fields, description="云枢智学 · 文本切片"))
    collection.create_index(
        "vector",
        {"index_type": "AUTOINDEX", "metric_type": "COSINE", "params": {}},
    )
    collection.load()
    logger.info("已创建集合 %s（维度 %s）", name, dimension)
    return collection


def replace_doc_chunks(
    name: str, doc_id: int, chunks: list[dict], vectors: list[list[float]]
) -> int:
    """先删该文档的旧切片再写入，保证重复处理不产生重复数据。"""
    collection = ensure_collection(name)

    try:
        collection.delete(f"doc_id == {doc_id}")
        collection.flush()
    except Exception:
        # 首次写入时集合为空，删除报错可忽略
        pass

    if not chunks:
        return 0

    rows = [
        [f"{doc_id}-{index}" for index in range(len(chunks))],
        [doc_id] * len(chunks),
        [int(item["index"]) for item in chunks],
        [_truncate_bytes(item.get("title", ""), TITLE_MAX) for item in chunks],
        [_truncate_bytes(item["content"], CONTENT_MAX) for item in chunks],
        vectors,
    ]
    collection.insert(rows)
    collection.flush()
    return len(chunks)


def delete_doc(name: str, doc_id: int) -> None:
    try:
        collection = ensure_collection(name)
        collection.delete(f"doc_id == {doc_id}")
        collection.flush()
    except Exception as exc:
        logger.warning("删除切片失败 doc=%s：%s", doc_id, type(exc).__name__)


def search(
    name: str, vector: list[float], top_k: int = 5, doc_ids: list[int] | None = None
) -> list[dict]:
    """相似度检索，返回 [{doc_id, chunk_index, title, content, score}]。"""
    try:
        collection = ensure_collection(name)
    except api_error:
        raise

    expr = ""
    if doc_ids:
        joined = ", ".join(str(item) for item in doc_ids)
        expr = f"doc_id in [{joined}]"

    try:
        result = collection.search(
            data=[vector],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {}},
            limit=top_k,
            expr=expr or None,
            output_fields=["doc_id", "chunk_index", "title", "content"],
        )
    except Exception as exc:
        logger.warning("向量检索失败：%s", type(exc).__name__)
        raise api_error(10008, "检索失败，请稍后重试", 503)

    rows = []
    for hit in result[0]:
        entity = hit.entity
        rows.append(
            {
                "doc_id": int(entity.get("doc_id")),
                "chunk_index": int(entity.get("chunk_index")),
                "title": entity.get("title") or "",
                "content": entity.get("content") or "",
                "score": float(hit.score),
            }
        )
    return rows


def query_doc_chunks(name: str, doc_id: int, limit: int = 100) -> list[dict]:
    """按 doc_id 取全部切片（不做向量检索）。

    简历切片总量不大，直接全取再随机采样，比向量检索更不会漏掉项目经历。
    """
    try:
        collection = ensure_collection(name)
        rows = collection.query(
            expr=f"doc_id == {doc_id}",
            output_fields=["doc_id", "chunk_index", "title", "content"],
            limit=limit,
        )
    except Exception as exc:
        logger.warning("按文档读取切片失败 doc=%s：%s", doc_id, type(exc).__name__)
        raise api_error(10008, "简历读取失败，请稍后重试", 503)

    return [
        {
            "doc_id": int(item["doc_id"]),
            "chunk_index": int(item["chunk_index"]),
            "title": item.get("title") or "",
            "content": item.get("content") or "",
            "score": 0.0,
        }
        for item in rows
    ]


def collection_stats(name: str) -> dict:
    try:
        collection = ensure_collection(name)
        collection.flush()
        return {"name": name, "entities": collection.num_entities}
    except api_error:
        return {"name": name, "entities": 0}
