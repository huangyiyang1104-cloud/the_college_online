"""B2 学科管理：增删改查、检索关键词、课程排序。

规则：学科名唯一（未删除范围内）；学科下仍有课程时禁止删除。
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import api_error, conflict, not_found
from app.models import subject
from app.repositories import course_admin_repo, subject_admin_repo
from app.services import audit_service


def _dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def _rows(db: Session, items: list[subject]) -> list[dict]:
    """批量补关键词与课程数，避免逐条查询。"""
    ids = [item.id for item in items]
    keywords = subject_admin_repo.keywords_map(db, ids)
    counts = subject_admin_repo.course_count_map(db, ids)
    return [
        {
            "id": str(item.id),
            "name": item.name,
            "icon": item.icon,
            "description": item.description,
            "sort_order": item.sort_order,
            "status": item.status,
            "keywords": keywords.get(item.id, []),
            "course_count": counts.get(item.id, 0),
            "created_at": _dt(item.created_at),
        }
        for item in items
    ]


def _load(db: Session, subject_id: int) -> subject:
    item = subject_admin_repo.get_active(db, subject_id)
    if not item:
        raise not_found("学科不存在")
    return item


def _ensure_name_unique(db: Session, name: str, exclude_id: int | None = None) -> None:
    if subject_admin_repo.find_by_name(db, name, exclude_id):
        raise conflict("学科名称已存在", 30002)


def list_subjects(
    status: int | None, keyword: str | None, page: int, page_size: int, db: Session
) -> tuple[list[dict], int]:
    items, total = subject_admin_repo.paginate(
        db, status, keyword, (page - 1) * page_size, page_size
    )
    return _rows(db, items), total


def create(body, admin_id: int, db: Session) -> dict:
    _ensure_name_unique(db, body.name)
    item = subject_admin_repo.add(
        db,
        subject(
            name=body.name,
            icon=body.icon,
            description=body.description,
            sort_order=body.sort_order,
            status=1,
        ),
    )
    subject_admin_repo.replace_keywords(db, item.id, body.keywords)

    audit_service.record(db, admin_id, "课程内容", "新增", "subject", item.id, item.name)
    db.commit()
    db.refresh(item)
    return _rows(db, [item])[0]


def get(subject_id: int, db: Session) -> dict:
    return _rows(db, [_load(db, subject_id)])[0]


def update(subject_id: int, body, admin_id: int, db: Session) -> dict:
    item = _load(db, subject_id)
    before = _rows(db, [item])[0]

    if body.name and body.name != item.name:
        _ensure_name_unique(db, body.name, exclude_id=subject_id)
        item.name = body.name
    if body.icon is not None:
        item.icon = body.icon
    if body.description is not None:
        item.description = body.description
    if body.sort_order is not None:
        item.sort_order = body.sort_order
    if body.status is not None:
        item.status = body.status
    if body.keywords is not None:
        subject_admin_repo.replace_keywords(db, subject_id, body.keywords)

    item.updated_at = utcnow()
    db.flush()

    after = _rows(db, [item])[0]
    audit_service.record(
        db, admin_id, "课程内容", "编辑", "subject", item.id, item.name, before, after
    )
    db.commit()
    return after


def delete(subject_id: int, admin_id: int, db: Session) -> None:
    item = _load(db, subject_id)

    remain = subject_admin_repo.count_courses(db, subject_id)
    if remain:
        raise api_error(30001, f"该学科下还有 {remain} 门课程，请先删除或下架课程", 409)

    subject_admin_repo.soft_delete(db, item, utcnow())
    audit_service.record(db, admin_id, "课程内容", "删除", "subject", item.id, item.name)
    db.commit()


def reorder_courses(subject_id: int, course_ids: list[int], admin_id: int, db: Session) -> dict:
    _load(db, subject_id)
    if not course_ids:
        raise api_error(10001, "course_ids 不能为空", 400)

    rows = course_admin_repo.list_by_subject(db, subject_id)
    if set(course_ids) != {row.id for row in rows}:
        raise api_error(30003, "顺序参数与课程集合不匹配", 400)

    positions = {course_id: index + 1 for index, course_id in enumerate(course_ids)}
    course_admin_repo.apply_sort_orders(db, rows, positions)

    audit_service.record(
        db, admin_id, "课程内容", "调整顺序", "subject", subject_id, f"共 {len(rows)} 门"
    )
    db.commit()
    return {"updated": len(rows)}
