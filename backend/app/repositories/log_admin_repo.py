"""后台操作日志的数据访问。"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import admin_operation_log, admin_user


def paginate(
    db: Session,
    module: str | None,
    action: str | None,
    admin_user_id: int | None,
    start_at: datetime | None,
    end_at: datetime | None,
    offset: int,
    limit: int,
) -> tuple[list[admin_operation_log], int]:
    stmt = select(admin_operation_log)
    if module:
        stmt = stmt.where(admin_operation_log.module == module)
    if action:
        stmt = stmt.where(admin_operation_log.action == action)
    if admin_user_id:
        stmt = stmt.where(admin_operation_log.admin_user_id == admin_user_id)
    if start_at:
        stmt = stmt.where(admin_operation_log.created_at >= start_at)
    if end_at:
        stmt = stmt.where(admin_operation_log.created_at <= end_at)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.execute(
            stmt.order_by(admin_operation_log.id.desc()).offset(offset).limit(limit)
        ).scalars()
    )
    return items, total


def admin_name_map(db: Session, admin_ids: list[int]) -> dict[int, str]:
    if not admin_ids:
        return {}
    rows = db.execute(
        select(admin_user.id, admin_user.username).where(admin_user.id.in_(admin_ids))
    ).all()
    return {row[0]: row[1] for row in rows}


def add(db: Session, row: admin_operation_log) -> admin_operation_log:
    db.add(row)
    return row
