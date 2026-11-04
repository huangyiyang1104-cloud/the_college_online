"""B4 面试资料库：上传、状态管理、失败重投、删除、检索测试。

文档切分与向量化属于异步任务（Celery + MinerU + Embedding），
本阶段只打通「上传 → 建记录 → 状态流转 → 删除」的主链路；
切分任务接入后由 worker 把 status 从 1 推进到 3、失败置 4。
"""

from datetime import datetime

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import settings_cache
from app.core.errors import api_error, conflict, not_found
from app.integrations import embedding, minio_storage, vector_store
from app.models import interview_doc
from app.repositories import doc_admin_repo
from app.services import audit_service, ingest_service

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_SUFFIX = {".pdf": 1, ".md": 2}
STATUS_FAILED = 4
STATUS_PENDING = 1
# 2 = 处理中：正常不应重试，但进程中断会卡在这个状态，允许手动恢复
STATUS_PROCESSING = 2


def _dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def _row(item: interview_doc) -> dict:
    return {
        "id": str(item.id),
        "file_name": item.file_name,
        "file_type": item.file_type,
        "file_size": item.file_size,
        "status": item.status,
        "failure_reason": item.failure_reason,
        "uploaded_by": str(item.uploaded_by),
        "created_at": _dt(item.created_at),
    }


def _load(db: Session, doc_id: int) -> interview_doc:
    item = doc_admin_repo.get_active(db, doc_id)
    if not item:
        raise not_found("文档不存在")
    return item


def list_docs(
    status: int | None, keyword: str | None, page: int, page_size: int, db: Session
) -> tuple[list[dict], int]:
    items, total = doc_admin_repo.paginate(
        db, status, keyword, (page - 1) * page_size, page_size
    )
    return [_row(item) for item in items], total


def upload(file: UploadFile, admin_id: int, db: Session) -> dict:
    filename = file.filename or ""
    suffix = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    file_type = ALLOWED_SUFFIX.get(suffix)
    if not file_type:
        raise api_error(60001, "仅支持 pdf / md 文件", 400)

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise api_error(60002, "文件超过 10 MB 限制", 413)

    object_key = minio_storage.upload(content, suffix, file.content_type)

    item = doc_admin_repo.add(
        db,
        interview_doc(
            file_name=filename[:255],
            file_type=file_type,
            file_size=len(content),
            oss_key=object_key,
            status=STATUS_PENDING,
            failure_reason="",
            uploaded_by=admin_id,
        ),
    )
    audit_service.record(
        db, admin_id, "面试资料库", "上传", "interview_doc", item.id, item.file_name
    )
    db.commit()
    db.refresh(item)
    return _row(item)


def get(doc_id: int, db: Session) -> dict:
    return _row(_load(db, doc_id))


def retry(doc_id: int, admin_id: int, db: Session) -> dict:
    """触发（重新）解析入库：待处理、失败都可重试，同步执行后返回切片数。"""
    item = _load(db, doc_id)
    # 允许「处理中」重试：异常中断会让状态卡在 2，需要人工救回
    if item.status not in (STATUS_PENDING, STATUS_PROCESSING, STATUS_FAILED):
        raise conflict("仅待处理、处理中或失败的文档可以重新处理")

    result = ingest_service.process_doc(doc_id, db)
    audit_service.record(
        db,
        admin_id,
        "面试资料库",
        "重新处理",
        "interview_doc",
        item.id,
        f"{item.file_name}（{result.get('chunks')} 片）",
    )
    db.commit()
    return result


def delete(doc_id: int, admin_id: int, db: Session) -> None:
    item = _load(db, doc_id)
    doc_admin_repo.soft_delete(db, item, utcnow())
    audit_service.record(
        db, admin_id, "面试资料库", "删除", "interview_doc", item.id, item.file_name
    )
    db.commit()
    # 同步清理向量切片，避免检索到已删除的文档
    ingest_service.delete_doc_chunks(doc_id)


def retrieval_test(subject_id: int | None, query: str | None, top_k: int) -> dict:
    """向量检索测试：把 query 向量化后从 Milvus 取最相似的 top_k 个切片。"""
    if not (query or "").strip():
        raise api_error(10001, "query 不能为空", 400)

    vector = embedding.embed_texts([query.strip()])[0]
    hits = vector_store.search(
        settings_cache.milvus_collection_docs, vector, top_k=top_k
    )
    return {
        "query": query.strip(),
        "items": [
            {
                "doc_id": str(hit["doc_id"]),
                "chunk_index": hit["chunk_index"],
                "title": hit["title"],
                "content": hit["content"],
                "score": round(hit["score"], 4),
            }
            for hit in hits
        ],
    }
