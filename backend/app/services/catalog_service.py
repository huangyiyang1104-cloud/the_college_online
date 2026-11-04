"""C2 学科与课程节点图：进度计算、推荐下一课、访问去重、点亮。

学科完成率与推荐下一课实时计算，不落库。
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.clock import beijing_day_start_utc, utcnow
from app.core.errors import not_found
from app.models import course, course_completion, learning_visit, subject, user
from app.repositories import course_repo, learning_repo, subject_repo

RECENT_VISIT_LIMIT = 3


def _dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def _group_by_subject(courses: list[course]) -> dict[int, list[course]]:
    grouped: dict[int, list[course]] = {}
    for item in courses:
        grouped.setdefault(item.subject_id, []).append(item)
    return grouped


def _progress(nodes: list[course], completed: dict[int, datetime]) -> dict:
    total = len(nodes)
    done = sum(1 for item in nodes if item.id in completed)
    return {
        "course_count": total,
        "completed_count": done,
        "progress_percent": round(done * 100 / total) if total else 0,
    }


def _next_course(nodes: list[course], completed: dict[int, datetime]) -> course | None:
    return next((node for node in nodes if node.id not in completed), None)


def _subject_basic(item: subject, nodes: list[course], completed: dict) -> dict:
    data = {
        "id": str(item.id),
        "name": item.name,
        "icon": item.icon,
        "description": item.description,
    }
    data.update(_progress(nodes, completed))
    return data


def _subject_with_next(item: subject, nodes: list[course], completed: dict) -> dict:
    data = _subject_basic(item, nodes, completed)
    next_node = _next_course(nodes, completed)
    data["next_course"] = (
        {"id": str(next_node.id), "title": next_node.title} if next_node else None
    )
    return data


def home(current: user, db: Session) -> dict:
    subjects = subject_repo.list_published(db)
    courses = course_repo.list_published_by_subjects(db, [item.id for item in subjects])
    grouped = _group_by_subject(courses)
    completed = learning_repo.completed_map(db, current.id, [item.id for item in courses])

    cards = [
        _subject_with_next(item, grouped.get(item.id, []), completed) for item in subjects
    ]

    visits = learning_repo.recent_visits(db, current.id, RECENT_VISIT_LIMIT)
    recent = [
        {
            "course_id": str(row[0].course_id),
            "course_title": row[1],
            "subject_id": str(row[2]),
            "subject_name": row[3],
            "visited_at": _dt(row[0].visited_at),
            "is_completed": row[0].course_id in completed,
        }
        for row in visits
    ]
    return {"subjects": cards, "recent_visits": recent}


def list_subjects(current: user, page: int, page_size: int, db: Session) -> tuple[list[dict], int]:
    items, total = subject_repo.paginate_published(db, (page - 1) * page_size, page_size)
    courses = course_repo.list_published_by_subjects(db, [item.id for item in items])
    grouped = _group_by_subject(courses)
    completed = learning_repo.completed_map(
        db, current.id, [node.id for nodes in grouped.values() for node in nodes]
    )
    cards = [_subject_basic(item, grouped.get(item.id, []), completed) for item in items]
    return cards, total


def subject_detail(current: user, subject_id: int, db: Session) -> dict:
    item = subject_repo.get_published(db, subject_id)
    if not item:
        raise not_found("学科不存在")

    nodes = course_repo.list_published_by_subjects(db, [subject_id])
    completed = learning_repo.completed_map(db, current.id, [node.id for node in nodes])

    data = _subject_basic(item, nodes, completed)
    next_node = _next_course(nodes, completed)
    data["recommended_course_id"] = str(next_node.id) if next_node else None
    data["nodes"] = [
        {
            "id": str(node.id),
            "sort_order": node.sort_order,
            "title": node.title,
            "description": node.description,
            "duration_minutes": node.duration_minutes,
            "bilibili_url": node.bilibili_url,
            "is_completed": node.id in completed,
            "completed_at": _dt(completed.get(node.id)),
        }
        for node in nodes
    ]
    return data


def record_visit(current: user, course_id: int, db: Session) -> tuple[dict, bool]:
    """按「学员 + 课程 + 北京时间自然日」去重；返回 (数据, 是否新增)。"""
    if not course_repo.get_published(db, course_id):
        raise not_found("课程不存在或已下架")

    day_start = beijing_day_start_utc()
    day_end = day_start + timedelta(days=1)

    existing = learning_repo.find_visit_in_range(db, current.id, course_id, day_start, day_end)
    if existing:
        return {"id": str(existing.id), "visited_at": _dt(existing.visited_at)}, False

    row = learning_repo.add_visit(
        db, learning_visit(user_id=current.id, course_id=course_id, visited_at=utcnow())
    )
    db.commit()
    db.refresh(row)
    return {"id": str(row.id), "visited_at": _dt(row.visited_at)}, True


def mark_completed(current: user, course_id: int, db: Session) -> dict:
    """点亮节点，幂等：已点亮返回原时间。"""
    if not course_repo.get_published(db, course_id):
        raise not_found("课程不存在或已下架")

    existing = learning_repo.get_completion(db, current.id, course_id)
    if existing:
        return {"course_id": str(course_id), "completed_at": _dt(existing.completed_at)}

    row = learning_repo.add_completion(
        db,
        course_completion(user_id=current.id, course_id=course_id, completed_at=utcnow()),
    )
    db.commit()
    # 必须回读：MySQL DATETIME 对小数秒取整，直接用 Python 的 now 会与库里的值差 1 秒，
    # 导致"重复点亮幂等"看起来时间变了
    db.refresh(row)
    return {"course_id": str(course_id), "completed_at": _dt(row.completed_at)}


def unmark_completed(current: user, course_id: int, db: Session) -> None:
    """取消点亮，幂等。"""
    learning_repo.delete_completion(db, current.id, course_id)
    db.commit()
