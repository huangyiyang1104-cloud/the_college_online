"""简历数据访问。

同一学员只保留一份有效简历：重新上传时旧的置 deleted_at，
查询永远取最新那份未删除的记录。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NOT_DELETED, resume


def get_active(db: Session, user_id: int) -> resume | None:
    return db.execute(
        select(resume)
        .where(resume.user_id == user_id, resume.deleted_at == NOT_DELETED)
        .order_by(resume.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_by_id(db: Session, resume_id: int) -> resume | None:
    return db.get(resume, resume_id)


def add(db: Session, row: resume) -> resume:
    db.add(row)
    db.flush()
    return row
