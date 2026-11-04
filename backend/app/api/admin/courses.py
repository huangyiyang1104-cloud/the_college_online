"""B2 课程管理接口（controller），业务在 services/admin_course_service。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.db import get_db
from app.core.errors import ok
from app.models import admin_user
from app.schemas import course_create, course_update
from app.services import admin_course_service

router = APIRouter(tags=["admin-courses"])


@router.get("/admin/subjects/{subject_id}/courses")
def list_courses(
    subject_id: int,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(admin_course_service.list_by_subject(subject_id, db))


@router.post("/admin/subjects/{subject_id}/courses", status_code=201)
def create_course(
    subject_id: int,
    body: course_create,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(admin_course_service.create(subject_id, body, current.id, db))


@router.patch("/admin/courses/{course_id}")
def update_course(
    course_id: int,
    body: course_update,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(admin_course_service.update(course_id, body, current.id, db))


@router.delete("/admin/courses/{course_id}", status_code=204)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    admin_course_service.delete(course_id, current.id, db)
    return None
