"""时间工具：库内统一存 UTC（naive datetime，与建表脚本一致）。

业务上的"自然日"（每日配额、访问去重）按北京时间计算，这里统一提供换算。
"""

from datetime import datetime, timedelta, timezone

BEIJING_OFFSET = timedelta(hours=8)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def beijing_day_start_utc(days_ago: int = 0) -> datetime:
    """返回"北京时间的某天 0 点"对应的 UTC 时间，用于区间查询。"""
    beijing_now = datetime.now(timezone.utc) + BEIJING_OFFSET
    day_start = datetime(beijing_now.year, beijing_now.month, beijing_now.day) - timedelta(
        days=days_ago
    )
    return day_start - BEIJING_OFFSET
