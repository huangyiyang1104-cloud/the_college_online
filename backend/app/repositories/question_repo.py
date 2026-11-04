"""题库的数据访问（学员端：组卷与判分用）。"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NOT_DELETED, question, question_option


def list_published_brief(db: Session, subject_id: int) -> list[tuple[int, int, Decimal]]:
    """返回 (id, type, score)，供组卷抽样使用（不带题干，数据量小）。"""
    rows = db.execute(
        select(question.id, question.type, question.score).where(
            question.subject_id == subject_id,
            question.deleted_at == NOT_DELETED,
            question.status == 1,
        )
    ).all()
    return [(row[0], row[1], row[2]) for row in rows]


def list_by_ids(db: Session, question_ids: list[int]) -> list[question]:
    if not question_ids:
        return []
    return list(
        db.execute(
            select(question).where(
                question.id.in_(question_ids),
                question.deleted_at == NOT_DELETED,
                question.status == 1,
            )
        ).scalars()
    )


def options_map(db: Session, question_ids: list[int]) -> dict[int, list[tuple[str, str, int]]]:
    """选项：{question_id: [(option_key, content, is_correct)]}，按展示顺序。"""
    if not question_ids:
        return {}
    result: dict[int, list[tuple[str, str, int]]] = {}
    rows = db.execute(
        select(
            question_option.question_id,
            question_option.option_key,
            question_option.content,
            question_option.is_correct,
        )
        .where(question_option.question_id.in_(question_ids))
        .order_by(question_option.question_id, question_option.sort_order, question_option.option_key)
    ).all()
    for question_id, option_key, content, is_correct in rows:
        result.setdefault(question_id, []).append((option_key, content, is_correct))
    return result
