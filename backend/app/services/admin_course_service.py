"""B2 课程管理：增删改查。课程挂在学科下，按 sort_order 构成学习路径。"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import conflict, not_found
from app.models import course
from app.repositories import course_admin_repo, subject_admin_repo
from app.services import audit_service


def _dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def _rows(courses: list[course]) -> list[dict]:
    return [
        {
            "id": str(item.id),
            "subject_id": str(item.subject_id),
            "title": item.title,
            "description": item.description,
            "duration_minutes": item.duration_minutes,
            "bilibili_url": item.bilibili_url,
            "sort_order": item.sort_order,
            "status": item.status,
            "created_at": _dt(item.created_at),
        }
        for item in courses
    ]


def _ensure_subject(db: Session, subject_id: int) -> None:
    if not subject_admin_repo.get_active(db, subject_id):
        raise not_found("学科不存在")


def _load(db: Session, course_id: int) -> course:
    item = course_admin_repo.get_active(db, course_id)
    if not item:
        raise not_found("课程不存在")
    return item


def _ensure_title_unique(
    db: Session, subject_id: int, title: str, exclude_id: int | None = None
) -> None:
    if course_admin_repo.find_by_title(db, subject_id, title, exclude_id):
        raise conflict("同学科下课程标题已存在", 30002)


def list_by_subject(subject_id: int, db: Session) -> dict:
    _ensure_subject(db, subject_id)
    rows = course_admin_repo.list_by_subject(db, subject_id)
    return {"list": _rows(rows), "total": len(rows)}


def create(subject_id: int, body, admin_id: int, db: Session) -> dict:
    _ensure_subject(db, subject_id)
    _ensure_title_unique(db, subject_id, body.title)

    sort_order = (
        body.sort_order
        if body.sort_order is not None
        else course_admin_repo.max_sort_order(db, subject_id) + 1
    )
    item = course_admin_repo.add(
        db,
        course(
            subject_id=subject_id,
            title=body.title,
            description=body.description,
            duration_minutes=body.duration_minutes,
            bilibili_url=body.bilibili_url,
            sort_order=sort_order,
            status=1,
        ),
    )

    audit_service.record(db, admin_id, "课程内容", "新增", "course", item.id, item.title)
    db.commit()
    db.refresh(item)
    return _rows([item])[0]


def update(course_id: int, body, admin_id: int, db: Session) -> dict:
    item = _load(db, course_id)
    before = _rows([item])[0]

    if body.title and body.title != item.title:
        _ensure_title_unique(db, item.subject_id, body.title, exclude_id=course_id)
        item.title = body.title
    if body.description is not None:
        item.description = body.description
    if body.duration_minutes is not None:
        item.duration_minutes = body.duration_minutes
    if body.bilibili_url is not None:
        item.bilibili_url = body.bilibili_url
    if body.status is not None:
        item.status = body.status

    item.updated_at = utcnow()
    db.flush()

    after = _rows([item])[0]
    audit_service.record(
        db, admin_id, "课程内容", "编辑", "course", item.id, item.title, before, after
    )
    db.commit()
    return after


def delete(course_id: int, admin_id: int, db: Session) -> None:
    item = _load(db, course_id)
    course_admin_repo.soft_delete(db, item, utcnow())
    audit_service.record(db, admin_id, "课程内容", "删除", "course", item.id, item.title)
    db.commit()
