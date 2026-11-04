"""学员账号的数据访问。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import user, user_login_log


def get_by_id(db: Session, user_id: int) -> user | None:
    return db.get(user, user_id)


def get_by_phone(db: Session, phone: str) -> user | None:
    return db.execute(select(user).where(user.phone == phone)).scalar_one_or_none()


def add(db: Session, account: user) -> user:
    db.add(account)
    db.flush()
    return account


def add_login_log(db: Session, user_id: int, login_at, ip: str = "") -> None:
    db.add(user_login_log(user_id=user_id, login_at=login_at, ip=ip))


def paginate(
    db: Session, keyword: str | None, status: int | None, offset: int, limit: int
) -> tuple[list[user], int]:
    """管理端学员列表：按手机号或昵称模糊搜索。"""
    stmt = select(user)
    if keyword:
        stmt = stmt.where(user.phone.like(f"%{keyword}%") | user.nickname.like(f"%{keyword}%"))
    if status is not None:
        stmt = stmt.where(user.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.execute(stmt.order_by(user.id.desc()).offset(offset).limit(limit)).scalars()
    )
    return items, total
