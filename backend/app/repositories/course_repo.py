"""课程的数据访问（学员端只读）。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NOT_DELETED, course


def list_published_by_subjects(db: Session, subject_ids: list[int]) -> list[course]:
    """一次查出这批学科的上架课程，按「学科 → 学习顺序」排序。"""
    if not subject_ids:
        return []
    rows = db.execute(
        select(course)
        .where(
            course.subject_id.in_(subject_ids),
            course.deleted_at == NOT_DELETED,
            course.status == 1,
        )
        .order_by(course.subject_id, course.sort_order, course.id)
    ).scalars()
    return list(rows)


def get_published(db: Session, course_id: int) -> course | None:
    item = db.get(course, course_id)
    if not item or item.deleted_at != NOT_DELETED or item.status != 1:
        return None
    return item
