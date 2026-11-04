"""后台认证接口（controller），业务在 services/admin_auth_service。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.db import get_db
from app.core.errors import ok
from app.models import admin_user
from app.schemas import login_request, refresh_request
from app.services import admin_auth_service

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


@router.post("/login")
def admin_login(body: login_request, db: Session = Depends(get_db)):
    return ok(admin_auth_service.login(body.username, body.password, db))


@router.post("/tokens")
def admin_refresh(body: refresh_request, db: Session = Depends(get_db)):
    return ok(admin_auth_service.refresh(body.refresh_token, db))


@router.post("/logout")
def admin_logout(
    current: admin_user = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return ok(admin_auth_service.logout(current, db))


@router.get("/me")
def admin_me(current: admin_user = Depends(get_current_admin)):
    return ok(admin_auth_service.me(current))
