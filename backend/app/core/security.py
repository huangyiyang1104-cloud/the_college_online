"""密码哈希与 JWT 双 token。"""

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings_cache
from app.core.errors import unauthorized

PASSWORD_ITERATIONS = 260000
JWT_ALGORITHM = "HS256"


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def hash_password(raw_password: str) -> str:
    """Base64 编码的 PBKDF2，控制在 90 字符内，适配 password_hash VARCHAR(100)。"""
    salt = _b64(secrets.token_bytes(16))
    digest = hashlib.pbkdf2_hmac(
        "sha256", raw_password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${_b64(digest)}"


def verify_password(raw_password: str, stored_hash: str) -> bool:
    try:
        _algo, iterations, salt, digest = stored_hash.split("$")
        calc = hashlib.pbkdf2_hmac(
            "sha256", raw_password.encode("utf-8"), salt.encode("utf-8"), int(iterations)
        )
        return hmac.compare_digest(_b64(calc), digest)
    except (ValueError, TypeError):
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject_id: int, audience: str = "admin", role: int | None = None) -> str:
    """audience 区分学员端（student）与后台（admin），互不通用。"""
    expire = _now() + timedelta(minutes=settings_cache.access_token_minutes)
    payload = {
        "sub": str(subject_id),
        "aud": audience,
        "jti": uuid.uuid4().hex,
        "iat": int(_now().timestamp()),
        "exp": int(expire.timestamp()),
    }
    if role is not None:
        payload["role"] = role
    return jwt.encode(payload, settings_cache.jwt_secret, algorithm=JWT_ALGORITHM)


def create_refresh_token(subject_id: int) -> tuple[str, str, datetime]:
    """返回 (token, jti, 过期时间)。refresh 自身不做签名载荷，靠 Redis 白名单校验。"""
    jti = uuid.uuid4().hex
    expire = _now() + timedelta(days=settings_cache.refresh_token_days)
    token = f"{jti}.{secrets.token_urlsafe(24)}"
    return token, jti, expire


def decode_access_token(token: str, audience: str = "admin") -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings_cache.jwt_secret,
            algorithms=[JWT_ALGORITHM],
            audience=audience,
        )
    except jwt.ExpiredSignatureError:
        raise unauthorized("登录已过期，请重新登录")
    except jwt.PyJWTError:
        raise unauthorized()
    return payload
