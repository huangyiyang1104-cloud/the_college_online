"""依赖注入：数据库会话、分页参数、后台/学员身份校验。"""

from fastapi import Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.cache import is_admin_revoked
from app.core.db import get_db
from app.core.errors import forbidden, unauthorized
from app.core.security import decode_access_token
from app.models import admin_user, user
from app.repositories import admin_user_repo, user_repo

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def get_current_admin(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> admin_user:
    if not authorization.lower().startswith("bearer "):
        raise unauthorized("缺少访问令牌")
    payload = decode_access_token(authorization[7:].strip())

    admin_id = int(payload.get("sub", 0))
    if is_admin_revoked(admin_id, int(payload.get("iat", 0))):
        raise unauthorized("账号状态已变更，请重新登录")

    account = admin_user_repo.get_by_id(db, admin_id)
    if not account:
        raise unauthorized()
    if account.status != 1:
        raise forbidden("账号已被停用")
    return account


def get_current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> user:
    """学员端鉴权：token 的 aud 必须是 student，后台 token 不能访问学员接口。"""
    if not authorization.lower().startswith("bearer "):
        raise unauthorized("缺少访问令牌")
    payload = decode_access_token(authorization[7:].strip(), audience="student")

    account = user_repo.get_by_id(db, int(payload.get("sub", 0)))
    if not account:
        raise unauthorized()
    if account.status != 1:
        raise forbidden("账号已被停用")
    return account


def require_super_admin(current: admin_user = Depends(get_current_admin)) -> admin_user:
    if current.role != 1:
        raise forbidden("仅超管可执行该操作")
    return current


class page_params:
    """分页参数：page 从 1 开始，page_size 上限 100。"""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
        page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


# 审计日志已统一到 services/audit_service.record（controller 不再直接写日志）
