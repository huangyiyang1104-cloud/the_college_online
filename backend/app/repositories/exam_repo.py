"""答卷（整卷提交）的数据访问。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import exam_answer, exam_answer_option, exam_paper, subject


def add_paper(db: Session, item: exam_paper) -> exam_paper:
    db.add(item)
    db.flush()
    return item


def add_answer(db: Session, item: exam_answer) -> exam_answer:
    db.add(item)
    db.flush()
    return item


def add_answer_options(db: Session, rows: list[exam_answer_option]) -> None:
    for row in rows:
        db.add(row)


def get_paper(db: Session, paper_id: int, user_id: int) -> exam_paper | None:
    """只返回本人答卷，他人查不到（避免越权）。"""
    return db.execute(
        select(exam_paper).where(exam_paper.id == paper_id, exam_paper.user_id == user_id)
    ).scalar_one_or_none()


def paginate_papers(
    db: Session, user_id: int, subject_id: int | None, offset: int, limit: int
) -> tuple[list[exam_paper], int]:
    stmt = select(exam_paper).where(exam_paper.user_id == user_id)
    if subject_id:
        stmt = stmt.where(exam_paper.subject_id == subject_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.execute(
            stmt.order_by(exam_paper.submitted_at.desc(), exam_paper.id.desc())
            .offset(offset)
            .limit(limit)
        ).scalars()
    )
    return items, total


def answers_by_paper(db: Session, paper_id: int) -> list[exam_answer]:
    return list(
        db.execute(
            select(exam_answer).where(exam_answer.paper_id == paper_id).order_by(exam_answer.id)
        ).scalars()
    )


def answer_options_map(db: Session, answer_ids: list[int]) -> dict[int, list[exam_answer_option]]:
    if not answer_ids:
        return {}
    result: dict[int, list[exam_answer_option]] = {}
    rows = db.execute(
        select(exam_answer_option)
        .where(exam_answer_option.answer_id.in_(answer_ids))
        .order_by(exam_answer_option.answer_id, exam_answer_option.option_key)
    ).scalars()
    for row in rows:
        result.setdefault(row.answer_id, []).append(row)
    return result


def subject_name_map(db: Session, subject_ids: list[int]) -> dict[int, str]:
    if not subject_ids:
        return {}
    rows = db.execute(select(subject.id, subject.name).where(subject.id.in_(subject_ids))).all()
    return {row[0]: row[1] for row in rows}
