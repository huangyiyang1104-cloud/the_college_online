"""C3 学习记录：访问流水列表与汇总统计。"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import user
from app.repositories import learning_repo


def _dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def list_records(
    current: user, subject_id: int | None, page: int, page_size: int, db: Session
) -> tuple[list[dict], int]:
    rows, total = learning_repo.paginate_visits(
        db, current.id, subject_id, (page - 1) * page_size, page_size
    )
    # 只为当前页课程查一次点亮状态
    completed = learning_repo.completed_course_ids(
        db, current.id, [row[0].course_id for row in rows]
    )

    items = [
        {
            "course_id": str(row[0].course_id),
            "course_title": row[1],
            "subject_id": str(row[2]),
            "subject_name": row[3],
            "visited_at": _dt(row[0].visited_at),
            "is_completed": row[0].course_id in completed,
        }
        for row in rows
    ]
    return items, total


def summary(current: user, db: Session) -> dict:
    return {
        "visited_count": learning_repo.count_visits(db, current.id),
        "completed_count": learning_repo.count_completions(db, current.id),
        "subject_count": learning_repo.count_completed_subjects(db, current.id),
    }
