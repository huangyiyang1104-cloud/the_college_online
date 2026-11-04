"""学习数据（访问流水 + 点亮状态）的数据访问。"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import NOT_DELETED, course, course_completion, learning_visit, subject


def completed_map(db: Session, user_id: int, course_ids: list[int]) -> dict[int, datetime]:
    if not course_ids:
        return {}
    rows = db.execute(
        select(course_completion.course_id, course_completion.completed_at).where(
            course_completion.user_id == user_id,
            course_completion.course_id.in_(course_ids),
        )
    ).all()
    return {row[0]: row[1] for row in rows}


def completed_course_ids(db: Session, user_id: int, course_ids: list[int]) -> set[int]:
    if not course_ids:
        return set()
    rows = db.execute(
        select(course_completion.course_id).where(
            course_completion.user_id == user_id,
            course_completion.course_id.in_(course_ids),
        )
    ).scalars()
    return set(rows)


def find_visit_in_range(
    db: Session, user_id: int, course_id: int, start: datetime, end: datetime
) -> learning_visit | None:
    """查指定时间区间内的访问记录（用于按自然日去重）。"""
    return db.execute(
        select(learning_visit)
        .where(
            learning_visit.user_id == user_id,
            learning_visit.course_id == course_id,
            learning_visit.visited_at >= start,
            learning_visit.visited_at < end,
        )
        .order_by(learning_visit.id)
        .limit(1)
    ).scalar_one_or_none()


def add_visit(db: Session, row: learning_visit) -> learning_visit:
    db.add(row)
    db.flush()
    return row


def recent_visits(db: Session, user_id: int, limit: int):
    """最近访问（带课程与学科名），已删除课程不出现。"""
    return db.execute(
        select(learning_visit, course.title, course.subject_id, subject.name)
        .join(course, course.id == learning_visit.course_id)
        .join(subject, subject.id == course.subject_id)
        .where(learning_visit.user_id == user_id, course.deleted_at == NOT_DELETED)
        .order_by(learning_visit.visited_at.desc(), learning_visit.id.desc())
        .limit(limit)
    ).all()


def paginate_visits(
    db: Session, user_id: int, subject_id: int | None, offset: int, limit: int
):
    stmt = (
        select(learning_visit, course.title, course.subject_id, subject.name)
        .join(course, course.id == learning_visit.course_id)
        .join(subject, subject.id == course.subject_id)
        .where(learning_visit.user_id == user_id, course.deleted_at == NOT_DELETED)
    )
    if subject_id:
        stmt = stmt.where(course.subject_id == subject_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(learning_visit.visited_at.desc(), learning_visit.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return rows, total


def get_completion(db: Session, user_id: int, course_id: int) -> course_completion | None:
    return db.execute(
        select(course_completion).where(
            course_completion.user_id == user_id,
            course_completion.course_id == course_id,
        )
    ).scalar_one_or_none()


def add_completion(db: Session, row: course_completion) -> course_completion:
    db.add(row)
    db.flush()
    return row


def delete_completion(db: Session, user_id: int, course_id: int) -> None:
    db.query(course_completion).filter(
        course_completion.user_id == user_id,
        course_completion.course_id == course_id,
    ).delete()


def completed_count_map(db: Session, user_ids: list[int]) -> dict[int, int]:
    """批量统计每个学员的点亮课程数，避免逐行查询。"""
    if not user_ids:
        return {}
    rows = db.execute(
        select(course_completion.user_id, func.count(course_completion.id))
        .where(course_completion.user_id.in_(user_ids))
        .group_by(course_completion.user_id)
    ).all()
    return {row[0]: int(row[1]) for row in rows}


def count_visits(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.count(learning_visit.id)).where(learning_visit.user_id == user_id)
    ) or 0


def count_completions(db: Session, user_id: int) -> int:
    return db.scalar(
        select(func.count(course_completion.id)).where(course_completion.user_id == user_id)
    ) or 0


def count_completed_subjects(db: Session, user_id: int) -> int:
    """有完成记录的去重学科数（已删除课程不计）。"""
    return db.scalar(
        select(func.count(func.distinct(course.subject_id)))
        .select_from(course_completion)
        .join(course, course.id == course_completion.course_id)
        .where(course_completion.user_id == user_id, course.deleted_at == NOT_DELETED)
    ) or 0
