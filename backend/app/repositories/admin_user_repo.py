"""后台账号的数据访问。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import admin_user

ROLE_SUPER = 1


def get_by_id(db: Session, admin_id: int) -> admin_user | None:
    return db.get(admin_user, admin_id)


def get_by_username(db: Session, username: str) -> admin_user | None:
    return db.execute(
        select(admin_user).where(admin_user.username == username)
    ).scalar_one_or_none()


def exists_username(db: Session, username: str) -> bool:
    return db.execute(select(admin_user.id).where(admin_user.username == username)).first() is not None


def paginate(db: Session, offset: int, limit: int) -> tuple[list[admin_user], int]:
    stmt = select(admin_user)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.execute(stmt.order_by(admin_user.id).offset(offset).limit(limit)).scalars())
    return items, total


def count_active_super_admins(db: Session) -> int:
    return db.scalar(
        select(func.count(admin_user.id)).where(
            admin_user.role == ROLE_SUPER, admin_user.status == 1
        )
    ) or 0


def add(db: Session, account: admin_user) -> admin_user:
    db.add(account)
    db.flush()
    return account


def delete(db: Session, account: admin_user) -> None:
    db.delete(account)
