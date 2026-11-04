"""数据库连接与会话管理（同步 SQLAlchemy，避免异步驱动额外复杂度）。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings_cache

engine = create_engine(
    settings_cache.database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def get_db() -> Generator[Session, None, None]:
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
