"""B3 刷题题库：按学科维护四类题型。

规则（已确认）：
  - 客观题至少一个正确选项，选项标识不可重复，判断题只允许 A/B；
  - 简答题不设选项，必须填写参考答案；
  - 不支持修改题型（改题型等同于重录）。
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import api_error, not_found
from app.models import question
from app.repositories import question_admin_repo, subject_admin_repo
from app.services import audit_service

TYPE_JUDGE = 1
TYPE_SHORT_ANSWER = 4


def _dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def _rows(db: Session, items: list[question]) -> list[dict]:
    ids = [item.id for item in items]
    options = question_admin_repo.options_map(db, ids)
    tags = question_admin_repo.tags_map(db, ids)
    subjects = subject_admin_repo.name_map(db, list({item.subject_id for item in items}))

    return [
        {
            "id": str(item.id),
            "subject_id": str(item.subject_id),
            "subject_name": subjects.get(item.subject_id, ""),
            "type": item.type,
            "difficulty": item.difficulty,
            "category": item.category,
            "title": item.title,
            "score": float(item.score),
            "status": item.status,
            "options": [
                {
                    "option_key": option.option_key,
                    "content": option.content,
                    "is_correct": option.is_correct,
                }
                for option in options.get(item.id, [])
            ],
            "reference_answer": item.reference_answer or "",
            "analysis": item.analysis or "",
            "tags": tags.get(item.id, []),
            "created_at": _dt(item.created_at),
        }
        for item in items
    ]


def _ensure_subject(db: Session, subject_id: int) -> None:
    if not subject_admin_repo.get_active(db, subject_id):
        raise not_found("学科不存在")


def _load(db: Session, question_id: int) -> question:
    item = question_admin_repo.get_active(db, question_id)
    if not item:
        raise not_found("题目不存在")
    return item


def _validate_options(q_type: int, options: list) -> None:
    if q_type == TYPE_SHORT_ANSWER:
        if options:
            raise api_error(10001, "简答题不能设置选项", 400)
        return

    if not options:
        raise api_error(10001, "客观题必须设置选项", 400)
    if not any(item.is_correct == 1 for item in options):
        raise api_error(10001, "客观题至少需要一个正确选项", 400)

    keys = [item.option_key.upper() for item in options]
    if len(keys) != len(set(keys)):
        raise api_error(10001, "选项标识不能重复", 400)
    if q_type == TYPE_JUDGE and set(keys) - {"A", "B"}:
        raise api_error(10001, "判断题只允许 A / B 两个选项", 400)


def list_questions(
    subject_id: int | None,
    q_type: int | None,
    status: int | None,
    keyword: str | None,
    page: int,
    page_size: int,
    db: Session,
) -> tuple[list[dict], int]:
    items, total = question_admin_repo.paginate(
        db, subject_id, q_type, status, keyword, (page - 1) * page_size, page_size
    )
    return _rows(db, items), total


def create(body, admin_id: int, db: Session) -> dict:
    _ensure_subject(db, body.subject_id)
    _validate_options(body.type, body.options)

    if body.type == TYPE_SHORT_ANSWER and not (body.reference_answer or "").strip():
        raise api_error(10001, "简答题必须填写参考答案", 400)

    item = question_admin_repo.add(
        db,
        question(
            subject_id=body.subject_id,
            type=body.type,
            difficulty=body.difficulty,
            category=body.category,
            title=body.title,
            score=body.score,
            reference_answer=body.reference_answer if body.type == TYPE_SHORT_ANSWER else None,
            analysis=body.analysis,
            status=1,
        ),
    )
    question_admin_repo.replace_options(db, item.id, body.options)
    question_admin_repo.replace_tags(db, item.id, body.tags)

    audit_service.record(db, admin_id, "刷题题库", "新增", "question", item.id, body.title[:60])
    db.commit()
    db.refresh(item)
    return _rows(db, [item])[0]


def update(question_id: int, body, admin_id: int, db: Session) -> dict:
    item = _load(db, question_id)
    before = _rows(db, [item])[0]

    if body.subject_id is not None and body.subject_id != item.subject_id:
        _ensure_subject(db, body.subject_id)
        item.subject_id = body.subject_id
    if body.difficulty is not None:
        item.difficulty = body.difficulty
    if body.category is not None:
        item.category = body.category
    if body.title is not None:
        item.title = body.title
    if body.score is not None:
        item.score = body.score
    if body.analysis is not None:
        item.analysis = body.analysis
    if body.status is not None:
        item.status = body.status

    if item.type == TYPE_SHORT_ANSWER:
        if body.reference_answer is not None:
            item.reference_answer = body.reference_answer
    elif body.options is not None:
        _validate_options(item.type, body.options)
        question_admin_repo.replace_options(db, item.id, body.options)

    if body.tags is not None:
        question_admin_repo.replace_tags(db, item.id, body.tags)

    item.updated_at = utcnow()
    db.flush()

    after = _rows(db, [item])[0]
    audit_service.record(
        db, admin_id, "刷题题库", "编辑", "question", item.id, item.title[:60], before, after
    )
    db.commit()
    return after


def delete(question_id: int, admin_id: int, db: Session) -> None:
    item = _load(db, question_id)
    question_admin_repo.soft_delete(db, item, utcnow())
    audit_service.record(
        db, admin_id, "刷题题库", "删除", "question", item.id, item.title[:60]
    )
    db.commit()
