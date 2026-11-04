"""学员端个人信息接口（controller），业务在 services/user_service。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.errors import ok
from app.models import user
from app.schemas import profile_update
from app.services import user_service

router = APIRouter(prefix="/users", tags=["student-users"])


@router.get("/me")
def get_me(
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(user_service.profile(current, db))


@router.patch("/me")
def update_me(
    body: profile_update,
    current: user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(user_service.update_profile(current, body.nickname, body.city, db))
