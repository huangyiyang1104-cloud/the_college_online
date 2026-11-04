"""B5 学员管理接口（controller），业务在 services/admin_student_service。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, page_params
from app.core.db import get_db
from app.core.errors import ok, paged
from app.models import admin_user
from app.schemas import status_update
from app.services import admin_student_service

router = APIRouter(prefix="/admin/students", tags=["admin-students"])


@router.get("")
def list_students(
    keyword: str | None = Query(default=None, max_length=64),
    status: int | None = Query(default=None, ge=0, le=1),
    pagination: page_params = Depends(page_params),
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    items, total = admin_student_service.list_students(
        keyword, status, pagination.page, pagination.page_size, db
    )
    return ok(paged(items, total, pagination.page, pagination.page_size))


@router.patch("/{student_id}")
def update_student_status(
    student_id: int,
    body: status_update,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(admin_student_service.update_status(student_id, body.status, current.id, db))
