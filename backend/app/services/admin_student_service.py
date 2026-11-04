"""B5 学员管理：列表与启用/禁用。

按已确认范围，不展示简历、刷题与面试结果。
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import not_found
from app.models import user
from app.repositories import learning_repo, user_repo
from app.services import audit_service


def _dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def _rows(db: Session, items: list[user]) -> list[dict]:
    # 批量统计点亮课程数，避免逐行查询
    counts = learning_repo.completed_count_map(db, [item.id for item in items])
    return [
        {
            "id": str(item.id),
            "phone": item.phone,
            "nickname": item.nickname,
            "created_at": _dt(item.created_at),
            "completed_course_count": counts.get(item.id, 0),
            "status": item.status,
        }
        for item in items
    ]


def list_students(
    keyword: str | None, status: int | None, page: int, page_size: int, db: Session
) -> tuple[list[dict], int]:
    items, total = user_repo.paginate(db, keyword, status, (page - 1) * page_size, page_size)
    return _rows(db, items), total


def update_status(student_id: int, status: int, admin_id: int, db: Session) -> dict:
    item = user_repo.get_by_id(db, student_id)
    if not item:
        raise not_found("学员不存在")

    item.status = status
    item.updated_at = utcnow()
    audit_service.record(
        db,
        admin_id,
        "学员管理",
        "启用" if status == 1 else "停用",
        "user",
        item.id,
        item.phone,
    )
    db.commit()
    return {"id": str(item.id), "status": item.status}
