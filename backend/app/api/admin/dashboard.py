"""B1 数据看板接口（controller），业务在 services/dashboard_service。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.db import get_db
from app.core.errors import ok
from app.models import admin_user
from app.services import dashboard_service

router = APIRouter(prefix="/admin/dashboard", tags=["admin-dashboard"])


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current: admin_user = Depends(get_current_admin),
):
    return ok(dashboard_service.summary(db))
