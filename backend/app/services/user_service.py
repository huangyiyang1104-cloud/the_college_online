"""学员个人信息：查询与修改。"""

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.models import user
from app.repositories import user_stats_repo


def profile(current: user, db: Session) -> dict:
    return {
        "id": str(current.id),
        "phone": current.phone,
        "nickname": current.nickname,
        "city": current.city,
        "status": current.status,
        "created_at": current.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        if current.created_at
        else None,
        "stats": {
            key: user_stats_repo.count_by_user(db, table, current.id)
            for key, table in user_stats_repo.STAT_TABLES.items()
        },
    }


def update_profile(
    current: user, nickname: str | None, city: str | None, db: Session
) -> dict:
    """手机号不可修改（PRD 假设项），只允许改昵称与城市。"""
    if nickname is not None:
        current.nickname = nickname.strip()
    if city is not None:
        current.city = city.strip()

    current.updated_at = utcnow()
    db.commit()
    db.refresh(current)
    return profile(current, db)
