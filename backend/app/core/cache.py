"""Redis 用途：refresh token 白名单、禁用标记、导入任务临时结果。

导入任务不落库（与 03 数据库设计一致），TTL 30 分钟。
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import redis

from app.core.config import settings_cache

IMPORT_TTL_SECONDS = 1800
REFRESH_PREFIX = "auth:refresh:"
REVOKED_PREFIX = "auth:revoked:admin:"
IMPORT_PREFIX = "import:job:"

redis_client = redis.Redis(
    host=settings_cache.redis_host,
    port=settings_cache.redis_port,
    password=settings_cache.redis_password or None,
    db=settings_cache.redis_db,
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
)


# ---------- refresh token ----------
def save_refresh_token(jti: str, admin_id: int, expire_at: datetime) -> None:
    ttl = max(int((expire_at - datetime.now(expire_at.tzinfo)).total_seconds()), 1)
    redis_client.setex(f"{REFRESH_PREFIX}{jti}", ttl, str(admin_id))


def pop_refresh_token(jti: str) -> str | None:
    """轮换：取出即删除，旧 refresh 立即失效。"""
    key = f"{REFRESH_PREFIX}{jti}"
    admin_id = redis_client.get(key)
    if admin_id:
        redis_client.delete(key)
    return admin_id


# ---------- 禁用即失效 ----------
def mark_admin_revoked(admin_id: int) -> None:
    redis_client.set(f"{REVOKED_PREFIX}{admin_id}", str(int(datetime.now().timestamp())))


def is_admin_revoked(admin_id: int, issued_at: int) -> bool:
    revoked_at = redis_client.get(f"{REVOKED_PREFIX}{admin_id}")
    if not revoked_at:
        return False
    return issued_at < int(revoked_at)


# ---------- 短信验证码频控 ----------
SMS_COOLDOWN_PREFIX = "sms:cd:"
SMS_DAILY_PREFIX = "sms:day:"
# 验证码明文本身（阿里云模板要求调用方提供 ${code}，因此由我们生成并保管）
SMS_CODE_PREFIX = "sms:code:"


def save_sms_code(phone: str, code: str, ttl_seconds: int) -> None:
    redis_client.setex(f"{SMS_CODE_PREFIX}{phone}", ttl_seconds, code)


def verify_sms_code(phone: str, code: str) -> bool:
    """校验并一次性消费验证码，成功后立即删除，避免重放。"""
    key = f"{SMS_CODE_PREFIX}{phone}"
    saved = redis_client.get(key)
    if not saved or saved != code:
        return False
    redis_client.delete(key)
    return True


def _beijing_day() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y%m%d")


def try_acquire_sms_quota(phone: str, resend_seconds: int, daily_limit: int) -> str | None:
    """申请一次发码配额。

    返回 None 表示放行；否则返回限流原因：cooldown（重发太快）/ daily_limit（当日超限）。
    日期按北京时间划分，与看板口径一致。
    """
    cooldown_key = f"{SMS_COOLDOWN_PREFIX}{phone}"
    if not redis_client.set(cooldown_key, "1", ex=resend_seconds, nx=True):
        return "cooldown"

    daily_key = f"{SMS_DAILY_PREFIX}{phone}:{_beijing_day()}"
    count = redis_client.incr(daily_key)
    if count == 1:
        # 首次计数时设置过期，避免键永久堆积
        redis_client.expire(daily_key, 86400)
    if count > daily_limit:
        return "daily_limit"
    return None


# ---------- 导入任务 ----------
# ---------- 面试每日配额与语音票据 ----------
INTERVIEW_QUOTA_PREFIX = "interview:daily:"
WS_TICKET_PREFIX = "ws:ticket:"


def _interview_key(user_id: int) -> str:
    # 按北京时间自然日划分，与看板、访问去重口径一致
    return f"{INTERVIEW_QUOTA_PREFIX}{user_id}:{_beijing_day()}"


def get_interview_used(user_id: int) -> int:
    return int(redis_client.get(_interview_key(user_id)) or 0)


def incr_interview_used(user_id: int) -> int:
    """发起面试时调用（发起即扣，不退还）。"""
    key = _interview_key(user_id)
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 86400)
    return count


def save_ws_ticket(ticket: str, session_id: int, ttl_seconds: int = 60) -> None:
    redis_client.setex(f"{WS_TICKET_PREFIX}{ticket}", ttl_seconds, session_id)


def pop_ws_ticket(ticket: str) -> int | None:
    """取票即删，保证一次性。"""
    key = f"{WS_TICKET_PREFIX}{ticket}"
    value = redis_client.get(key)
    if not value:
        return None
    redis_client.delete(key)
    return int(value)


def save_import_job(job_id: str, payload: dict[str, Any]) -> None:
    redis_client.setex(f"{IMPORT_PREFIX}{job_id}", IMPORT_TTL_SECONDS, json.dumps(payload, ensure_ascii=False))


def load_import_job(job_id: str) -> dict[str, Any] | None:
    raw = redis_client.get(f"{IMPORT_PREFIX}{job_id}")
    return json.loads(raw) if raw else None


def drop_import_job(job_id: str) -> None:
    redis_client.delete(f"{IMPORT_PREFIX}{job_id}")
