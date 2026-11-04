"""B6 系统用户：仅超管可操作。

保护规则：内置账号不可删除/停用；不能停用或删除当前登录账号；至少保留一个启用的超管。
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.cache import mark_admin_revoked
from app.core.clock import utcnow
from app.core.errors import api_error, conflict, forbidden, not_found
from app.core.security import hash_password
from app.models import admin_user
from app.repositories import admin_user_repo
from app.services import audit_service

ROLE_SUPER = 1


def _dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def _rows(items: list[admin_user]) -> list[dict]:
    return [
        {
            "id": str(item.id),
            "username": item.username,
            "role": item.role,
            "is_builtin": item.is_builtin,
            "status": item.status,
            "created_at": _dt(item.created_at),
        }
        for item in items
    ]


def _load(db: Session, admin_id: int) -> admin_user:
    item = admin_user_repo.get_by_id(db, admin_id)
    if not item:
        raise not_found("后台账号不存在")
    return item


def list_users(page: int, page_size: int, db: Session) -> tuple[list[dict], int]:
    items, total = admin_user_repo.paginate(db, (page - 1) * page_size, page_size)
    return _rows(items), total


def create(body, operator_id: int, db: Session) -> dict:
    if admin_user_repo.exists_username(db, body.username):
        raise conflict("账号已存在", 30002)

    item = admin_user_repo.add(
        db,
        admin_user(
            username=body.username,
            password_hash=hash_password(body.password),
            role=body.role,
            is_builtin=0,
            status=1,
        ),
    )
    audit_service.record(db, operator_id, "系统用户", "新增", "admin_user", item.id, item.username)
    db.commit()
    db.refresh(item)
    return _rows([item])[0]


def update(target_id: int, body, current: admin_user, db: Session) -> dict:
    item = _load(db, target_id)

    if body.status is not None:
        if item.is_builtin == 1 and body.status == 0:
            raise conflict("内置账号不可停用")
        if item.id == current.id and body.status == 0:
            raise forbidden("不能停用当前登录账号")
        if (
            item.role == ROLE_SUPER
            and body.status == 0
            and admin_user_repo.count_active_super_admins(db) <= 1
        ):
            raise conflict("至少需要保留一个启用状态的超管")
        item.status = body.status
        if body.status == 0:
            mark_admin_revoked(item.id)

    if body.role is not None and body.role != item.role:
        if (
            item.role == ROLE_SUPER
            and body.role != ROLE_SUPER
            and admin_user_repo.count_active_super_admins(db) <= 1
        ):
            raise conflict("至少需要保留一个超管")
        item.role = body.role

    if body.password:
        item.password_hash = hash_password(body.password)
        mark_admin_revoked(item.id)

    item.updated_at = utcnow()
    audit_service.record(db, current.id, "系统用户", "编辑", "admin_user", item.id, item.username)
    db.commit()
    return _rows([item])[0]


def delete(target_id: int, current: admin_user, db: Session) -> None:
    item = _load(db, target_id)
    if item.is_builtin == 1:
        raise api_error(10005, "内置账号不可删除", 409)
    if item.id == current.id:
        raise forbidden("不能删除当前登录账号")
    if item.role == ROLE_SUPER and admin_user_repo.count_active_super_admins(db) <= 1:
        raise conflict("至少需要保留一个超管")

    username = item.username
    admin_user_repo.delete(db, item)
    audit_service.record(db, current.id, "系统用户", "删除", "admin_user", target_id, username)
    db.commit()
