"""错题本的数据访问。"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import NOT_DELETED, question, wrong_question

# 错题本只收录客观题
OBJECTIVE_TYPES = (1, 2, 3)


def get(db: Session, user_id: int, question_id: int) -> wrong_question | None:
    return db.execute(
        select(wrong_question).where(
            wrong_question.user_id == user_id, wrong_question.question_id == question_id
        )
    ).scalar_one_or_none()


def paginate(
    db: Session, user_id: int, subject_id: int | None, offset: int, limit: int
) -> tuple[list[wrong_question], int]:
    """只返回客观题且题目仍在架上（题目被删后错题自动隐藏）。"""
    stmt = (
        select(wrong_question)
        .join(question, question.id == wrong_question.question_id)
        .where(
            wrong_question.user_id == user_id,
            question.deleted_at == NOT_DELETED,
            question.type.in_(OBJECTIVE_TYPES),
        )
    )
    if subject_id:
        stmt = stmt.where(question.subject_id == subject_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.execute(
            stmt.order_by(wrong_question.last_wrong_at.desc(), wrong_question.id.desc())
            .offset(offset)
            .limit(limit)
        ).scalars()
    )
    return items, total


def delete_by_question(db: Session, user_id: int, question_id: int) -> int:
    """返回删除行数（0 表示本来不在错题本里）。"""
    return (
        db.query(wrong_question)
        .filter(wrong_question.user_id == user_id, wrong_question.question_id == question_id)
        .delete()
    )


def add(db: Session, item: wrong_question) -> wrong_question:
    db.add(item)
    db.flush()
    return item


def touch(db: Session, item: wrong_question, now: datetime) -> None:
    """再次答错：累计次数并刷新时间。"""
    item.wrong_times = (item.wrong_times or 0) + 1
    item.last_wrong_at = now
    item.updated_at = now
