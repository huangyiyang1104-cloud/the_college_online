"""C2 学科与课程节点图接口（controller）。

只负责 HTTP 编排：鉴权 → 调 service → 包装响应。
业务逻辑见 services/catalog_service，SQL 见 repositories/。
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, page_params
from app.core.db import get_db
from app.core.errors import ok, paged
from app.models import user
from app.services import catalog_service

router = APIRouter(tags=["student-catalog"])


@router.get("/home")
def home(
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(catalog_service.home(current, db))


@router.get("/subjects")
def list_subjects(
    pagination: page_params = Depends(page_params),
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = catalog_service.list_subjects(
        current, pagination.page, pagination.page_size, db
    )
    return ok(paged(items, total, pagination.page, pagination.page_size))


@router.get("/subjects/{subject_id}")
def subject_detail(
    subject_id: int,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(catalog_service.subject_detail(current, subject_id, db))


@router.post("/courses/{course_id}/visits")
def record_visit(
    course_id: int,
    response: Response,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data, created = catalog_service.record_visit(current, course_id, db)
    # 当日重复访问返回 200 与首次记录，首次访问返回 201
    response.status_code = 201 if created else 200
    return ok(data)


@router.put("/courses/{course_id}/completion")
def mark_completed(
    course_id: int,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(catalog_service.mark_completed(current, course_id, db))


@router.delete("/courses/{course_id}/completion", status_code=204)
def unmark_completed(
    course_id: int,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    catalog_service.unmark_completed(current, course_id, db)
    return None
