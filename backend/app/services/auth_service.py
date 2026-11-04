"""学员端认证：发码、注册、登录、刷新、退出。

验证码由服务端生成并通过 ${code} 传给阿里云模板，明文只存 Redis。
"""

from sqlalchemy.orm import Session

from app.core.cache import (
    pop_refresh_token,
    save_refresh_token,
    save_sms_code,
    try_acquire_sms_quota,
    verify_sms_code,
)
from app.core.clock import utcnow
from app.core.config import settings_cache
from app.core.errors import api_error
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.integrations.aliyun_pnvs import send_verify_code
from app.models import user
from app.repositories import user_repo


def _ensure_test_phone(phone: str) -> None:
    """测试期只允许白名单号码，名单与阿里云控制台需人工保持一致。"""
    if phone not in settings_cache.test_phone_list:
        raise api_error(20008, "当前仅支持测试号码，请先在阿里云控制台添加测试手机号", 403)


def _session(account: user, refresh_token: str) -> dict:
    return {
        "access_token": create_access_token(account.id, "student"),
        "refresh_token": refresh_token,
        "expires_in": settings_cache.access_token_minutes * 60,
        "user": {
            "id": str(account.id),
            "phone": account.phone,
            "nickname": account.nickname,
            "city": account.city,
            "created_at": account.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            if account.created_at
            else None,
        },
    }


def _record_login(db: Session, account: user) -> None:
    now = utcnow()
    account.last_login_at = now
    user_repo.add_login_log(db, account.id, now)


def _issue_tokens(db: Session, account: user) -> dict:
    token, jti, expire_at = create_refresh_token(account.id)
    save_refresh_token(jti, account.id, expire_at)
    return _session(account, token)


def send_code(phone: str, db: Session) -> dict:
    _ensure_test_phone(phone)

    if user_repo.get_by_phone(db, phone):
        raise api_error(20001, "该手机号已注册，请直接登录", 409)

    blocked = try_acquire_sms_quota(
        phone, settings_cache.sms_resend_seconds, settings_cache.sms_daily_limit
    )
    if blocked == "cooldown":
        raise api_error(
            20006, f"请求过于频繁，请 {settings_cache.sms_resend_seconds} 秒后再试", 429
        )
    if blocked == "daily_limit":
        raise api_error(20006, "今日验证码发送次数已达上限，请明天再试", 429)

    verify_code = send_verify_code(phone)
    save_sms_code(phone, verify_code, settings_cache.aliyun_pnvs_valid_minutes * 60)
    return {
        "expires_in": settings_cache.aliyun_pnvs_valid_minutes * 60,
        "resend_after": settings_cache.sms_resend_seconds,
    }


def register(phone: str, code: str, password: str, db: Session) -> dict:
    _ensure_test_phone(phone)

    if user_repo.get_by_phone(db, phone):
        raise api_error(20001, "该手机号已注册，请直接登录", 409)

    # 校验通过即消费验证码，防止重放
    if not verify_sms_code(phone, code):
        raise api_error(20002, "验证码错误或已过期", 400)

    account = user_repo.add(
        db,
        user(
            phone=phone,
            password_hash=hash_password(password),
            nickname="",
            city="",
            status=1,
        ),
    )
    _record_login(db, account)
    payload = _issue_tokens(db, account)
    db.commit()
    db.refresh(account)
    return payload


def login(phone: str, password: str, db: Session) -> dict:
    account = user_repo.get_by_phone(db, phone)
    if not account or not verify_password(password, account.password_hash):
        raise api_error(20003, "手机号或密码错误", 401)
    if account.status != 1:
        raise api_error(20004, "账号已被停用", 403)

    _record_login(db, account)
    payload = _issue_tokens(db, account)
    db.commit()
    db.refresh(account)
    return payload


def refresh(refresh_token: str, db: Session) -> dict:
    """刷新并轮换：旧 refresh 立即失效。"""
    jti = refresh_token.split(".", 1)[0]
    user_id = pop_refresh_token(jti)
    if not user_id:
        raise api_error(20005, "刷新令牌无效或已失效", 401)

    account = user_repo.get_by_id(db, int(user_id))
    if not account:
        raise api_error(20005, "刷新令牌无效或已失效", 401)
    if account.status != 1:
        raise api_error(20004, "账号已被停用", 403)

    return _issue_tokens(db, account)


def logout(current: user, db: Session) -> dict:
    """access token 短时效自然过期，前端清除本地令牌即可。"""
    return {"logged_out": True}
