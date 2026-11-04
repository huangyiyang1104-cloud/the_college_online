"""B1 数据看板：只统计学员规模与活跃，不含学习/刷题/面试指标。

口径（已确认）：按登录去重、北京时间自然日、近 7 天滚动。
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.clock import BEIJING_OFFSET, beijing_day_start_utc
from app.repositories import stats_admin_repo

TREND_DAYS = 7


def _trend(db: Session, week_start: datetime) -> list[dict]:
    """近 7 日注册趋势：按北京时间归日。"""
    counter: dict[str, int] = {}
    for created_at in stats_admin_repo.created_at_since(db, week_start):
        day = (created_at + BEIJING_OFFSET).strftime("%Y-%m-%d")
        counter[day] = counter.get(day, 0) + 1

    today = datetime.now(timezone.utc) + BEIJING_OFFSET
    return [
        {
            "date": (today - timedelta(days=offset)).strftime("%Y-%m-%d"),
            "count": counter.get((today - timedelta(days=offset)).strftime("%Y-%m-%d"), 0),
        }
        for offset in range(TREND_DAYS - 1, -1, -1)
    ]


def summary(db: Session) -> dict:
    today_start = beijing_day_start_utc(0)
    week_start = beijing_day_start_utc(TREND_DAYS - 1)

    return {
        "total_users": stats_admin_repo.count_users(db),
        "today_registered": stats_admin_repo.count_users_since(db, today_start),
        "today_active": stats_admin_repo.count_active_users_since(db, today_start),
        "week_active": stats_admin_repo.count_active_users_since(db, week_start),
        "week_registered": stats_admin_repo.count_users_since(db, week_start),
        "register_trend": _trend(db, week_start),
    }
