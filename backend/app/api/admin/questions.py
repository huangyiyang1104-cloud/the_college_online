"""B3 刷题题库接口（controller），业务在 services/admin_question_service。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, page_params
from app.core.db import get_db
from app.core.errors import ok, paged
from app.models import admin_user
from app.schemas import question_create, question_update
from app.services import admin_question_service

router = APIRouter(prefix="/admin/questions", tags=["admin-questions"])


@router.get("")
def list_questions(
    subject_id: int | None = Query(default=None),
    type: int | None = Query(default=None, ge=1, le=4),
    status: int | None = Query(default=None, ge=0, le=1),
    keyword: str | None = Query(default=None, max_length=64),
    pagination: page_params = Depends(page_params),
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    items, total = admin_question_service.list_questions(
        subject_id,
        type,
        status,
        keyword,
        pagination.page,
        pagination.page_size,
        db,
    )
    return ok(paged(items, total, pagination.page, pagination.page_size))


@router.post("", status_code=201)
def create_question(
    body: question_create,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(admin_question_service.create(body, current.id, db))


@router.patch("/{question_id}")
def update_question(
    question_id: int,
    body: question_update,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(admin_question_service.update(question_id, body, current.id, db))


@router.delete("/{question_id}", status_code=204)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    admin_question_service.delete(question_id, current.id, db)
    return None
