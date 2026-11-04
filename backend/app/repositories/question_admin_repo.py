"""刷题题库的数据访问（管理端）。"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import NOT_DELETED, question, question_option, question_tag


def paginate(
    db: Session,
    subject_id: int | None,
    q_type: int | None,
    status: int | None,
    keyword: str | None,
    offset: int,
    limit: int,
) -> tuple[list[question], int]:
    stmt = select(question).where(question.deleted_at == NOT_DELETED)
    if subject_id:
        stmt = stmt.where(question.subject_id == subject_id)
    if q_type:
        stmt = stmt.where(question.type == q_type)
    if status is not None:
        stmt = stmt.where(question.status == status)
    if keyword:
        stmt = stmt.where(question.title.like(f"%{keyword}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.execute(
            stmt.order_by(question.id.desc()).offset(offset).limit(limit)
        ).scalars()
    )
    return items, total


def get_active(db: Session, question_id: int) -> question | None:
    item = db.get(question, question_id)
    if not item or item.deleted_at != NOT_DELETED:
        return None
    return item


def add(db: Session, item: question) -> question:
    db.add(item)
    db.flush()
    return item


def soft_delete(db: Session, item: question, deleted_at: datetime) -> None:
    item.deleted_at = deleted_at


def options_map(db: Session, question_ids: list[int]) -> dict[int, list[question_option]]:
    if not question_ids:
        return {}
    result: dict[int, list[question_option]] = {}
    rows = db.execute(
        select(question_option)
        .where(question_option.question_id.in_(question_ids))
        .order_by(question_option.sort_order, question_option.option_key)
    ).scalars()
    for row in rows:
        result.setdefault(row.question_id, []).append(row)
    return result


def tags_map(db: Session, question_ids: list[int]) -> dict[int, list[str]]:
    if not question_ids:
        return {}
    result: dict[int, list[str]] = {}
    rows = db.execute(
        select(question_tag.question_id, question_tag.tag_name)
        .where(question_tag.question_id.in_(question_ids))
        .order_by(question_tag.id)
    )
    for question_id, tag in rows:
        result.setdefault(question_id, []).append(tag)
    return result


def replace_options(db: Session, question_id: int, options: list) -> None:
    db.query(question_option).filter(question_option.question_id == question_id).delete()
    for index, item in enumerate(options):
        db.add(
            question_option(
                question_id=question_id,
                option_key=item.option_key.upper(),
                content=item.content,
                is_correct=item.is_correct,
                sort_order=index,
            )
        )


def add_options(db: Session, question_id: int, options: list[dict]) -> None:
    """批量新增选项（导入用，入参是已校验的字典列表）。"""
    for index, item in enumerate(options):
        db.add(
            question_option(
                question_id=question_id,
                option_key=item["option_key"],
                content=item["content"],
                is_correct=item["is_correct"],
                sort_order=index,
            )
        )


def add_tags(db: Session, question_id: int, tags: list[str]) -> None:
    for tag in tags:
        db.add(question_tag(question_id=question_id, tag_name=tag))


def replace_tags(db: Session, question_id: int, tags: list[str]) -> None:
    db.query(question_tag).filter(question_tag.question_id == question_id).delete()
    for tag in tags:
        db.add(question_tag(question_id=question_id, tag_name=tag))
