"""课程的数据访问（管理端：含下架课程与排序）。"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import NOT_DELETED, course


def list_by_subject(db: Session, subject_id: int) -> list[course]:
    """该学科全部未删除课程（含下架），按学习顺序。"""
    return list(
        db.execute(
            select(course)
            .where(course.subject_id == subject_id, course.deleted_at == NOT_DELETED)
            .order_by(course.sort_order, course.id)
        ).scalars()
    )


def get_active(db: Session, course_id: int) -> course | None:
    item = db.get(course, course_id)
    if not item or item.deleted_at != NOT_DELETED:
        return None
    return item


def find_by_title(
    db: Session, subject_id: int, title: str, exclude_id: int | None = None
) -> course | None:
    stmt = select(course).where(
        course.subject_id == subject_id,
        course.title == title,
        course.deleted_at == NOT_DELETED,
    )
    if exclude_id:
        stmt = stmt.where(course.id != exclude_id)
    return db.execute(stmt.limit(1)).scalar_one_or_none()


def max_sort_order(db: Session, subject_id: int) -> int:
    return db.scalar(
        select(func.max(course.sort_order)).where(
            course.subject_id == subject_id, course.deleted_at == NOT_DELETED
        )
    ) or 0


def add(db: Session, item: course) -> course:
    db.add(item)
    db.flush()
    return item


def soft_delete(db: Session, item: course, deleted_at: datetime) -> None:
    item.deleted_at = deleted_at


def apply_sort_orders(db: Session, rows: list[course], positions: dict[int, int]) -> None:
    for row in rows:
        row.sort_order = positions[row.id]
