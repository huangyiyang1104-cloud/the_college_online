"""简历业务：上传 → 解析（PDF→文本→切片→向量化）→ 供简历面试出题。

状态机：1 待处理 → 2 解析中 → 3 就绪 / 4 失败。

切片写入独立集合（MILVUS_COLLECTION_RESUME），doc_id 直接用 resume.id：
不同学员的简历天然隔离，检索时带上 doc_ids 过滤即可，不会串到别人的简历。
"""

import logging
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import settings_cache
from app.core.errors import api_error, not_found
from app.integrations import embedding, minio_storage, pdf_parser, vector_store
from app.models import NOT_DELETED, resume, user
from app.repositories import resume_repo
from app.services import chunking

logger = logging.getLogger("yunshu.resume")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

STATUS_PENDING = 1
STATUS_PARSING = 2
STATUS_READY = 3
STATUS_FAILED = 4

MAX_BYTES = 10 * 1024 * 1024
PDF_MAGIC = b"%PDF"


def _collection() -> str:
    return settings_cache.milvus_collection_resume


def _iso(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def upload(current: user, file: UploadFile, db: Session) -> dict:
    """接收 PDF，落 MinIO 并建记录；解析由后台任务执行。"""
    content = file.file.read()
    if not content:
        raise api_error(60001, "文件为空", 400)

    # 按魔数判断而不是看扩展名：改后缀的 .docx 也能拦住
    if not content.startswith(PDF_MAGIC):
        raise api_error(60001, "仅支持 PDF 文件", 400)
    if len(content) > MAX_BYTES:
        raise api_error(60002, "文件超过 10MB 限制", 413)

    # 重新上传视为替换：旧简历软删并清掉它的切片
    old = resume_repo.get_active(db, current.id)
    if old:
        old.deleted_at = utcnow()
        db.flush()

    key = minio_storage.upload(content, ".pdf", "application/pdf")
    row = resume_repo.add(
        db,
        resume(
            user_id=current.id,
            file_name=(file.filename or "简历.pdf")[:255],
            file_size=len(content),
            oss_key=key,
            status=STATUS_PENDING,
            failure_reason="",
        ),
    )
    db.commit()
    db.refresh(row)

    if old:
        try:
            vector_store.delete_doc(_collection(), old.id)
        except Exception:
            logger.warning("清理旧简历切片失败 resume=%s", old.id)

    return {
        "id": str(row.id),
        "status": row.status,
        "file_name": row.file_name,
        "file_size": row.file_size,
    }


def parse(resume_id: int, db: Session) -> dict:
    """后台任务：下载 PDF → 提取文本 → 切片 → 向量化 → 写入简历集合。"""
    row = resume_repo.get_by_id(db, resume_id)
    if not row or row.deleted_at != NOT_DELETED:
        return {"id": str(resume_id), "status": STATUS_FAILED}

    row.status = STATUS_PARSING
    row.failure_reason = ""
    db.commit()

    try:
        content = minio_storage.download(row.oss_key)
        text = pdf_parser.extract_text(content)
        chunks = chunking.split_markdown(text)
        if not chunks:
            raise api_error(60003, "简历内容过少，无法切分", 422)

        vectors = embedding.embed_texts([item["content"] for item in chunks])
        vector_store.replace_doc_chunks(_collection(), row.id, chunks, vectors)

        row.status = STATUS_READY
        row.parsed_at = utcnow()
        row.failure_reason = ""
        db.commit()
        logger.info("简历 %s 解析完成：%s 片", resume_id, len(chunks))
        return {"id": str(row.id), "status": row.status, "chunks": len(chunks)}

    except Exception as exc:
        row.status = STATUS_FAILED
        row.failure_reason = (getattr(exc, "message", None) or str(exc))[:500]
        db.commit()
        logger.warning("简历 %s 解析失败：%s", resume_id, row.failure_reason)
        return {"id": str(row.id), "status": row.status}


def parse_task(resume_id: int) -> None:
    """后台任务入口：自建 session。

    FastAPI 的 get_db 在响应发出后就关闭了，后台任务不能复用请求的 session。
    """
    from app.core.db import session_factory

    with session_factory() as db:
        parse(resume_id, db)


def current(current: user, db: Session) -> dict:
    row = resume_repo.get_active(db, current.id)
    if not row:
        raise not_found("尚未上传简历")

    return {
        "id": str(row.id),
        "file_name": row.file_name,
        "file_size": row.file_size,
        "status": row.status,
        "failure_reason": row.failure_reason,
        "parsed_at": _iso(row.parsed_at),
        # 04 约定：项目经历不单独落库，由切片元数据组装；当前不做结构化提取
        "projects": [],
    }


def remove(current: user, db: Session) -> None:
    row = resume_repo.get_active(db, current.id)
    if not row:
        raise not_found("尚未上传简历")

    row.deleted_at = utcnow()
    db.commit()
    try:
        vector_store.delete_doc(_collection(), row.id)
    except Exception:
        logger.warning("删除简历切片失败 resume=%s", row.id)


def get_ready(current: user, db: Session) -> resume:
    """简历面试前置校验：必须存在且解析完成。"""
    row = resume_repo.get_active(db, current.id)
    if not row:
        raise api_error(60004, "请先上传简历", 409)
    if row.status != STATUS_READY:
        reason = row.failure_reason or "简历仍在解析中，请稍后再试"
        raise api_error(60004, reason, 409)
    return row
