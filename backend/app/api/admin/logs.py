"""B7 操作日志接口（controller），业务在 services/admin_log_service。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, page_params
from app.core.db import get_db
from app.core.errors import ok, paged
from app.models import admin_user
from app.services import admin_log_service

router = APIRouter(prefix="/admin/operation-logs", tags=["admin-logs"])


@router.get("")
def list_logs(
    module: str | None = Query(default=None, max_length=32),
    action: str | None = Query(default=None, max_length=32),
    admin_user_id: int | None = Query(default=None),
    start_at: str | None = Query(default=None, max_length=32),
    end_at: str | None = Query(default=None, max_length=32),
    with_detail: bool = Query(default=False),
    pagination: page_params = Depends(page_params),
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    items, total = admin_log_service.list_logs(
        module,
        action,
        admin_user_id,
        start_at,
        end_at,
        with_detail,
        pagination.page,
        pagination.page_size,
        db,
    )
    return ok(paged(items, total, pagination.page, pagination.page_size))
