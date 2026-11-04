"""B2 学科管理接口（controller），业务在 services/admin_subject_service。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, page_params
from app.core.db import get_db
from app.core.errors import ok, paged
from app.models import admin_user
from app.schemas import course_order_request, subject_create, subject_update
from app.services import admin_subject_service

router = APIRouter(prefix="/admin/subjects", tags=["admin-subjects"])


@router.get("")
def list_subjects(
    status: int | None = Query(default=None, ge=0, le=1),
    keyword: str | None = Query(default=None, max_length=64),
    pagination: page_params = Depends(page_params),
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    items, total = admin_subject_service.list_subjects(
        status, keyword, pagination.page, pagination.page_size, db
    )
    return ok(paged(items, total, pagination.page, pagination.page_size))


@router.post("", status_code=201)
def create_subject(
    body: subject_create,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(admin_subject_service.create(body, current.id, db))


@router.get("/{subject_id}")
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(admin_subject_service.get(subject_id, db))


@router.patch("/{subject_id}")
def update_subject(
    subject_id: int,
    body: subject_update,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(admin_subject_service.update(subject_id, body, current.id, db))


@router.delete("/{subject_id}", status_code=204)
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    admin_subject_service.delete(subject_id, current.id, db)
    return None


@router.put("/{subject_id}/courses/order")
def update_course_order(
    subject_id: int,
    body: course_order_request,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(admin_subject_service.reorder_courses(subject_id, body.course_ids, current.id, db))
