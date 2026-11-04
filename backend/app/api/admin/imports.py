"""批量导入接口（controller），业务在 services/import_service。"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.db import get_db
from app.core.errors import ok
from app.models import admin_user
from app.schemas import import_confirm
from app.services import import_service

router = APIRouter(tags=["admin-imports"])


@router.post("/admin/course-imports", status_code=201)
def create_course_import(
    file: UploadFile = File(...),
    subject_id: int = Form(...),
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(import_service.create_course_import(file, subject_id, current.id, db))


@router.patch("/admin/course-imports/{job_id}")
def confirm_course_import(
    job_id: str,
    body: import_confirm,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(import_service.confirm_course_import(job_id, current.id, db))


@router.post("/admin/question-imports", status_code=201)
def create_question_import(
    file: UploadFile = File(...),
    subject_id: int = Form(...),
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(import_service.create_question_import(file, subject_id, current.id, db))


@router.patch("/admin/question-imports/{job_id}")
def confirm_question_import(
    job_id: str,
    body: import_confirm,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(import_service.confirm_question_import(job_id, current.id, db))


@router.get("/admin/imports/{job_id}")
def get_import_job(
    job_id: str,
    current: admin_user = Depends(get_current_admin),
):
    return ok(import_service.get_job(job_id))
