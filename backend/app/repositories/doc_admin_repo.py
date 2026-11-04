"""面试资料库的数据访问。"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import NOT_DELETED, interview_doc


def paginate(
    db: Session, status: int | None, keyword: str | None, offset: int, limit: int
) -> tuple[list[interview_doc], int]:
    stmt = select(interview_doc).where(interview_doc.deleted_at == NOT_DELETED)
    if status:
        stmt = stmt.where(interview_doc.status == status)
    if keyword:
        stmt = stmt.where(interview_doc.file_name.like(f"%{keyword}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.execute(
            stmt.order_by(interview_doc.id.desc()).offset(offset).limit(limit)
        ).scalars()
    )
    return items, total


def get_active(db: Session, doc_id: int) -> interview_doc | None:
    item = db.get(interview_doc, doc_id)
    if not item or item.deleted_at != NOT_DELETED:
        return None
    return item


def add(db: Session, item: interview_doc) -> interview_doc:
    db.add(item)
    db.flush()
    return item


def soft_delete(db: Session, item: interview_doc, deleted_at: datetime) -> None:
    item.deleted_at = deleted_at
