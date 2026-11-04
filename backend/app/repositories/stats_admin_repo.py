"""看板统计的数据访问（只读聚合）。"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import user, user_login_log


def count_users(db: Session) -> int:
    return db.scalar(select(func.count(user.id))) or 0


def count_users_since(db: Session, since: datetime) -> int:
    return db.scalar(select(func.count(user.id)).where(user.created_at >= since)) or 0


def count_active_users_since(db: Session, since: datetime) -> int:
    """按登录去重的活跃人数。"""
    return db.scalar(
        select(func.count(func.distinct(user_login_log.user_id))).where(
            user_login_log.login_at >= since
        )
    ) or 0


def created_at_since(db: Session, since: datetime):
    """区间内的注册时间，供上层按自然日归集。"""
    return db.execute(select(user.created_at).where(user.created_at >= since)).scalars().all()
