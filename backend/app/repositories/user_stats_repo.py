"""学员个人中心的统计计数（跨多张业务表，表名为固定常量）。"""

from sqlalchemy import text
from sqlalchemy.orm import Session

STAT_TABLES = {
    "course_completed": "course_completion",
    "paper_count": "exam_paper",
    "wrong_count": "wrong_question",
    "interview_count": "interview_session",
}


def count_by_user(db: Session, table: str, user_id: int) -> int:
    """table 来自 STAT_TABLES 常量，不是外部输入。"""
    return db.scalar(text(f"SELECT COUNT(*) FROM {table} WHERE user_id = :uid"), {"uid": user_id}) or 0
