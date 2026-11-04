"""学员端认证接口（controller）。

只做参数接收与响应包装，业务逻辑在 services/auth_service，数据访问在 repositories/。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.errors import ok
from app.models import user
from app.schemas import (
    refresh_request,
    sms_code_request,
    student_login_request,
    student_register_request,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["student-auth"])


@router.post("/sms-codes")
def send_sms_code(body: sms_code_request, db: Session = Depends(get_db)):
    return ok(auth_service.send_code(body.phone, db))


@router.post("/register", status_code=201)
def register(body: student_register_request, db: Session = Depends(get_db)):
    return ok(auth_service.register(body.phone, body.code, body.password, db))


@router.post("/login")
def login(body: student_login_request, db: Session = Depends(get_db)):
    return ok(auth_service.login(body.phone, body.password, db))


@router.post("/tokens")
def refresh(body: refresh_request, db: Session = Depends(get_db)):
    return ok(auth_service.refresh(body.refresh_token, db))


@router.post("/logout")
def logout(current: user = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(auth_service.logout(current, db))
