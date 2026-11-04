"""面试会话与逐题记录的数据访问。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import interview_doc, interview_question, interview_session, subject


def add_session(db: Session, row: interview_session) -> interview_session:
    db.add(row)
    db.flush()
    return row


def get_session(db: Session, session_id: int) -> interview_session | None:
    return db.get(interview_session, session_id)


def add_question(db: Session, row: interview_question) -> interview_question:
    db.add(row)
    db.flush()
    return row


def list_questions(db: Session, session_id: int) -> list[interview_question]:
    return list(
        db.execute(
            select(interview_question)
            .where(interview_question.session_id == session_id)
            .order_by(interview_question.question_index)
        ).scalars()
    )


def get_question(db: Session, session_id: int, question_index: int) -> interview_question | None:
    return db.execute(
        select(interview_question).where(
            interview_question.session_id == session_id,
            interview_question.question_index == question_index,
        )
    ).scalar_one_or_none()


def paginate_sessions(
    db: Session, user_id: int, source: int | None, offset: int, limit: int
):
    """面试记录列表（带学科名）。"""
    stmt = (
        select(interview_session, subject.name)
        .outerjoin(subject, subject.id == interview_session.subject_id)
        .where(interview_session.user_id == user_id)
    )
    if source:
        stmt = stmt.where(interview_session.source == source)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(interview_session.started_at.desc(), interview_session.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return rows, total


def subject_name(db: Session, subject_id: int | None) -> str:
    """面试所属学科名；简历面试没有学科，返回空串。"""
    if not subject_id:
        return ""
    name = db.scalar(select(subject.name).where(subject.id == subject_id))
    return name or ""


def doc_names(db: Session, doc_ids: list[int]) -> dict[int, str]:
    """切片来源文档名快照（写入 interview_question.source_doc_name）。"""
    if not doc_ids:
        return {}
    rows = db.execute(
        select(interview_doc.id, interview_doc.file_name).where(interview_doc.id.in_(doc_ids))
    ).all()
    return {row[0]: row[1] for row in rows}


def count_sessions(db: Session, user_id: int) -> int:
    return (
        db.scalar(
            select(func.count(interview_session.id)).where(
                interview_session.user_id == user_id
            )
        )
        or 0
    )
