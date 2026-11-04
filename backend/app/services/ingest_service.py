"""资料库入库：下载原文 → 解析 → 切分 → 向量化 → 写入 Milvus。

状态流转（interview_doc.status）：
    1 待处理 → 2 处理中 → 3 已入库
                        ↘ 4 失败（failure_reason 记录原因）

PDF 目前未接入 MinerU 解析，会明确失败并提示改用 Markdown；
Markdown 走直读，速度可控（305KB 约 20 秒）。
"""

import logging

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import settings_cache
from app.core.db import session_factory
from app.core.errors import api_error, not_found
from app.integrations import embedding, minio_storage, vector_store
from app.repositories import doc_admin_repo
from app.services import chunking

logger = logging.getLogger("yunshu.ingest")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

STATUS_PENDING = 1
STATUS_PROCESSING = 2
STATUS_READY = 3
STATUS_FAILED = 4

FILE_TYPE_MD = 2


def _extract_text(file_type: int, content: bytes) -> str:
    if file_type == FILE_TYPE_MD:
        return content.decode("utf-8", "ignore")
    raise api_error(60005, "PDF 解析尚未接入（MinerU），请先上传 Markdown 文件", 422)


def process_doc(doc_id: int, db: Session) -> dict:
    """同步处理一份文档，返回 {id, status, chunks}。失败时抛 api_error 并落库原因。"""
    doc = doc_admin_repo.get_active(db, doc_id)
    if not doc:
        raise not_found("文档不存在")

    doc.status = STATUS_PROCESSING
    doc.failure_reason = ""
    doc.updated_at = utcnow()
    db.commit()

    try:
        content = minio_storage.download(doc.oss_key)
        text = _extract_text(doc.file_type, content)
        chunks = chunking.split_markdown(text)
        if not chunks:
            raise api_error(60004, "文档内容为空或过短，无法切分", 422)

        vectors = embedding.embed_texts([item["content"] for item in chunks])
        vector_store.replace_doc_chunks(
            settings_cache.milvus_collection_docs, doc.id, chunks, vectors
        )

        doc.status = STATUS_READY
        doc.failure_reason = ""
        doc.updated_at = utcnow()
        db.commit()
        logger.info("文档 %s 入库完成：%s 片", doc.id, len(chunks))
        return {"id": str(doc.id), "status": doc.status, "chunks": len(chunks)}

    except api_error as exc:
        doc.status = STATUS_FAILED
        doc.failure_reason = (exc.message or "")[:500]
        doc.updated_at = utcnow()
        db.commit()
        logger.warning("文档 %s 入库失败：%s", doc.id, exc.message)
        raise


def process_doc_background(doc_id: int) -> None:
    """后台任务入口：自己开 session，异常只记日志不影响请求。"""
    with session_factory() as db:
        try:
            process_doc(doc_id, db)
        except Exception as exc:
            logger.warning("后台入库失败 doc=%s：%s", doc_id, type(exc).__name__)


def delete_doc_chunks(doc_id: int) -> None:
    """文档删除时同步清掉向量切片。"""
    vector_store.delete_doc(settings_cache.milvus_collection_docs, doc_id)


def collection_overview() -> dict:
    return vector_store.collection_stats(settings_cache.milvus_collection_docs)
