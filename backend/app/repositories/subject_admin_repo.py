"""学科的数据访问（管理端：增删改查 + 关键词）。"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import NOT_DELETED, course, subject, subject_keyword


def paginate(
    db: Session,
    status: int | None,
    keyword: str | None,
    offset: int,
    limit: int,
) -> tuple[list[subject], int]:
    stmt = select(subject).where(subject.deleted_at == NOT_DELETED)
    if status is not None:
        stmt = stmt.where(subject.status == status)
    if keyword:
        stmt = stmt.where(subject.name.like(f"%{keyword}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.execute(
            stmt.order_by(subject.sort_order, subject.id).offset(offset).limit(limit)
        ).scalars()
    )
    return items, total


def get_active(db: Session, subject_id: int) -> subject | None:
    item = db.get(subject, subject_id)
    if not item or item.deleted_at != NOT_DELETED:
        return None
    return item


def find_by_name(db: Session, name: str, exclude_id: int | None = None) -> subject | None:
    stmt = select(subject).where(subject.name == name, subject.deleted_at == NOT_DELETED)
    if exclude_id:
        stmt = stmt.where(subject.id != exclude_id)
    return db.execute(stmt.limit(1)).scalar_one_or_none()


def add(db: Session, item: subject) -> subject:
    db.add(item)
    db.flush()
    return item


def soft_delete(db: Session, item: subject, deleted_at: datetime) -> None:
    item.deleted_at = deleted_at


def keywords_map(db: Session, subject_ids: list[int]) -> dict[int, list[str]]:
    if not subject_ids:
        return {}
    result: dict[int, list[str]] = {}
    rows = db.execute(
        select(subject_keyword.subject_id, subject_keyword.keyword)
        .where(subject_keyword.subject_id.in_(subject_ids))
        .order_by(subject_keyword.id)
    )
    for subject_id, keyword in rows:
        result.setdefault(subject_id, []).append(keyword)
    return result


def replace_keywords(db: Session, subject_id: int, keywords: list[str]) -> None:
    db.query(subject_keyword).filter(subject_keyword.subject_id == subject_id).delete()
    for keyword in keywords:
        db.add(subject_keyword(subject_id=subject_id, keyword=keyword))


def name_map(db: Session, subject_ids: list[int]) -> dict[int, str]:
    if not subject_ids:
        return {}
    rows = db.execute(select(subject.id, subject.name).where(subject.id.in_(subject_ids))).all()
    return {row[0]: row[1] for row in rows}


def course_count_map(db: Session, subject_ids: list[int]) -> dict[int, int]:
    if not subject_ids:
        return {}
    rows = db.execute(
        select(course.subject_id, func.count(course.id))
        .where(course.subject_id.in_(subject_ids), course.deleted_at == NOT_DELETED)
        .group_by(course.subject_id)
    ).all()
    return {row[0]: int(row[1]) for row in rows}


def count_courses(db: Session, subject_id: int) -> int:
    return db.scalar(
        select(func.count(course.id)).where(
            course.subject_id == subject_id, course.deleted_at == NOT_DELETED
        )
    ) or 0
