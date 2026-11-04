"""B6 系统用户接口（controller），业务在 services/admin_user_service，仅超管可访问。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import page_params, require_super_admin
from app.core.db import get_db
from app.core.errors import ok, paged
from app.models import admin_user
from app.schemas import admin_user_create, admin_user_update
from app.services import admin_user_service

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("")
def list_users(
    pagination: page_params = Depends(page_params),
    db: Session = Depends(get_db),
    current: admin_user = Depends(require_super_admin),
):
    items, total = admin_user_service.list_users(pagination.page, pagination.page_size, db)
    return ok(paged(items, total, pagination.page, pagination.page_size))


@router.post("", status_code=201)
def create_user(
    body: admin_user_create,
    db: Session = Depends(get_db),
    current: admin_user = Depends(require_super_admin),
):
    return ok(admin_user_service.create(body, current.id, db))


@router.patch("/{admin_id}")
def update_user(
    admin_id: int,
    body: admin_user_update,
    db: Session = Depends(get_db),
    current: admin_user = Depends(require_super_admin),
):
    return ok(admin_user_service.update(admin_id, body, current, db))


@router.delete("/{admin_id}", status_code=204)
def delete_user(
    admin_id: int,
    db: Session = Depends(get_db),
    current: admin_user = Depends(require_super_admin),
):
    admin_user_service.delete(admin_id, current, db)
    return None
