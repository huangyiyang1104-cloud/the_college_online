"""C5 错题本：列表、重做、移除。

规则（已确认）：
  - 只收录客观题，题目下架后被删的错题自动从列表隐藏；
  - 列表**不返回**正确选项与解析，重做后才给；
  - 重做答对即移出错题本（removed=true），答错累加 wrong_times。
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import api_error, not_found
from app.models import user
from app.repositories import question_repo, subject_repo, wrong_repo

OBJECTIVE_TYPES = (1, 2, 3)


def _dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def list_wrong(
    current: user, subject_id: int | None, page: int, page_size: int, db: Session
) -> tuple[list[dict], int]:
    items, total = wrong_repo.paginate(
        db, current.id, subject_id, (page - 1) * page_size, page_size
    )
    if not items:
        return [], total

    question_ids = [item.question_id for item in items]
    details = {row.id: row for row in question_repo.list_by_ids(db, question_ids)}
    options = question_repo.options_map(db, question_ids)
    names = subject_repo.name_map(db, list({row.subject_id for row in details.values()}))

    rows = []
    for item in items:
        detail = details.get(item.question_id)
        if not detail:
            continue
        rows.append(
            {
                "question_id": str(detail.id),
                "type": detail.type,
                "title": detail.title,
                "subject_id": str(detail.subject_id),
                "subject_name": names.get(detail.subject_id, ""),
                "wrong_times": item.wrong_times,
                "last_wrong_at": _dt(item.last_wrong_at),
                # 不返回 is_correct 与解析
                "options": [
                    {"option_key": key, "content": content}
                    for key, content, _ in options.get(detail.id, [])
                ],
            }
        )
    return rows, total


def attempt(
    current: user, question_id: int, option_keys: list[str], db: Session
) -> dict:
    details = question_repo.list_by_ids(db, [question_id])
    if not details:
        raise not_found("题目不存在或已下架")

    item = details[0]
    if item.type not in OBJECTIVE_TYPES:
        raise api_error(10001, "简答题不支持在错题本重做", 400)
    if not option_keys:
        raise api_error(10001, "option_keys 不能为空", 400)

    correct_keys = [
        key
        for key, _content, is_correct in question_repo.options_map(db, [question_id]).get(
            question_id, []
        )
        if is_correct == 1
    ]
    chosen_keys = [key.upper() for key in option_keys]
    is_correct = set(correct_keys) == set(chosen_keys)

    record = wrong_repo.get(db, current.id, question_id)
    removed = False
    if is_correct:
        if record:
            wrong_repo.delete_by_question(db, current.id, question_id)
            removed = True
    elif record:
        wrong_repo.touch(db, record, utcnow())

    db.commit()
    return {
        "is_correct": 1 if is_correct else 0,
        "correct_option_keys": correct_keys,
        "analysis": item.analysis or "",
        "removed": removed,
    }


def remove(current: user, question_id: int, db: Session) -> None:
    """手动移除，幂等：不在错题本里也返回成功。"""
    wrong_repo.delete_by_question(db, current.id, question_id)
    db.commit()
