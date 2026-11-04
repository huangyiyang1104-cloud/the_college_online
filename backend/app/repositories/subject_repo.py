"""学科的数据访问（学员端只读；管理端写入的查询在 admin 模块补）。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import NOT_DELETED, subject, subject_keyword


def list_published(db: Session) -> list[subject]:
    """上架且未删除的学科，按展示顺序。"""
    return list(
        db.execute(
            select(subject)
            .where(subject.status == 1, subject.deleted_at == NOT_DELETED)
            .order_by(subject.sort_order, subject.id)
        ).scalars()
    )


def paginate_published(db: Session, offset: int, limit: int) -> tuple[list[subject], int]:
    stmt = select(subject).where(subject.status == 1, subject.deleted_at == NOT_DELETED)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.execute(
            stmt.order_by(subject.sort_order, subject.id).offset(offset).limit(limit)
        ).scalars()
    )
    return items, total


def name_map(db: Session, subject_ids: list[int]) -> dict[int, str]:
    if not subject_ids:
        return {}
    rows = db.execute(select(subject.id, subject.name).where(subject.id.in_(subject_ids))).all()
    return {row[0]: row[1] for row in rows}


def get_published(db: Session, subject_id: int) -> subject | None:
    item = db.get(subject, subject_id)
    if not item or item.deleted_at != NOT_DELETED or item.status != 1:
        return None
    return item


def keywords_of(db: Session, subject_id: int) -> list[str]:
    """学科关键词，用于拼接检索 query。"""
    rows = db.execute(
        select(subject_keyword.keyword).where(subject_keyword.subject_id == subject_id)
    ).scalars()
    return [item for item in rows if item]
