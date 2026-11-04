"""C3 学习记录接口（controller），业务在 services/records_service。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, page_params
from app.core.db import get_db
from app.core.errors import ok, paged
from app.models import user
from app.services import records_service

router = APIRouter(prefix="/learning-records", tags=["student-records"])


@router.get("")
def list_records(
    subject_id: int | None = Query(default=None),
    pagination: page_params = Depends(page_params),
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = records_service.list_records(
        current, subject_id, pagination.page, pagination.page_size, db
    )
    return ok(paged(items, total, pagination.page, pagination.page_size))


@router.get("/summary")
def summary(
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(records_service.summary(current, db))
