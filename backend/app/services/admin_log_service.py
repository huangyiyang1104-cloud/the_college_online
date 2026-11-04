"""B7 操作日志查询：默认只返回摘要，需要前后快照时带 with_detail。"""

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import param_error
from app.repositories import log_admin_repo


def _parse_time(value: str | None, field: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise param_error(f"{field} 不是合法的 ISO 时间")


def list_logs(
    module: str | None,
    action: str | None,
    admin_user_id: int | None,
    start_at: str | None,
    end_at: str | None,
    with_detail: bool,
    page: int,
    page_size: int,
    db: Session,
) -> tuple[list[dict], int]:
    start = _parse_time(start_at, "start_at")
    end = _parse_time(end_at, "end_at")

    items, total = log_admin_repo.paginate(
        db, module, action, admin_user_id, start, end, (page - 1) * page_size, page_size
    )
    # 批量取操作人用户名
    names = log_admin_repo.admin_name_map(db, list({item.admin_user_id for item in items}))

    rows = []
    for item in items:
        record = {
            "id": str(item.id),
            "admin_user_id": str(item.admin_user_id),
            "admin_username": names.get(item.admin_user_id, ""),
            "module": item.module,
            "action": item.action,
            "target_type": item.target_type,
            "target_id": str(item.target_id) if item.target_id else None,
            "target_name": item.target_name,
            "created_at": item.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            if item.created_at
            else None,
        }
        if with_detail:
            record["detail_before"] = json.loads(item.detail_before) if item.detail_before else None
            record["detail_after"] = json.loads(item.detail_after) if item.detail_after else None
        rows.append(record)
    return rows, total
