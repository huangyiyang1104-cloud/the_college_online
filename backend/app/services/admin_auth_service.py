"""后台认证：登录、刷新（轮换）、退出、当前账号。"""

from sqlalchemy.orm import Session

from app.core.cache import pop_refresh_token, save_refresh_token
from app.core.config import settings_cache
from app.core.errors import api_error
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.models import admin_user
from app.repositories import admin_user_repo
from app.services import audit_service


def _session(account: admin_user, refresh_token: str) -> dict:
    return {
        "access_token": create_access_token(account.id, "admin", account.role),
        "refresh_token": refresh_token,
        "expires_in": settings_cache.access_token_minutes * 60,
        "admin_user": {
            "id": str(account.id),
            "username": account.username,
            "role": account.role,
            "is_builtin": account.is_builtin,
        },
    }


def login(username: str, password: str, db: Session) -> dict:
    account = admin_user_repo.get_by_username(db, username)
    if not account or not verify_password(password, account.password_hash):
        raise api_error(20003, "账号或密码错误", 401)
    if account.status != 1:
        raise api_error(20004, "账号已被停用", 403)

    token, jti, expire_at = create_refresh_token(account.id)
    save_refresh_token(jti, account.id, expire_at)
    audit_service.record(
        db, account.id, "系统用户", "登录", "admin_user", account.id, account.username
    )
    db.commit()
    return _session(account, token)


def refresh(refresh_token: str, db: Session) -> dict:
    jti = refresh_token.split(".", 1)[0]
    admin_id = pop_refresh_token(jti)
    if not admin_id:
        raise api_error(20005, "刷新令牌无效或已失效", 401)

    account = admin_user_repo.get_by_id(db, int(admin_id))
    if not account or account.status != 1:
        raise api_error(20004, "账号不可用，请重新登录", 403)

    token, new_jti, expire_at = create_refresh_token(account.id)
    save_refresh_token(new_jti, account.id, expire_at)
    return _session(account, token)


def logout(current: admin_user, db: Session) -> dict:
    audit_service.record(
        db, current.id, "系统用户", "退出", "admin_user", current.id, current.username
    )
    db.commit()
    return {"logged_out": True}


def me(current: admin_user) -> dict:
    return {
        "id": str(current.id),
        "username": current.username,
        "role": current.role,
        "is_builtin": current.is_builtin,
        "created_at": current.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        if current.created_at
        else None,
    }
