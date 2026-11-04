"""C4 刷题：按学科随机组卷。

规则（已确认）：每套 20 题，判断 4 / 单选 8 / 多选 4 / 简答 4；
某题型不足用其他题型补足；题池不足 20 题时按实际题量组卷；同一套卷内题目不重复。
"""

import random
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import api_error, not_found
from app.models import question, user
from app.repositories import question_repo, subject_repo

PAPER_SIZE = 20
# (题型, 目标题量)：1 判断、2 单选、3 多选、4 简答
TYPE_PLAN = ((1, 4), (2, 8), (3, 4), (4, 4))
# 卷面展示顺序：单选 → 多选 → 判断 → 简答
# 单选排第一是因为它的题池最大，能保证每套卷开头不重复；简答放最后便于集中作答
TYPE_ORDER = {2: 0, 3: 1, 1: 2, 4: 3}


def _sample(brief: list[tuple[int, int, Decimal]]) -> list[tuple[int, int, Decimal]]:
    """按题型比例抽样，不足时用其他题型补足。"""
    by_type: dict[int, list[tuple[int, int, Decimal]]] = {}
    for item in brief:
        by_type.setdefault(item[1], []).append(item)

    picked: list[tuple[int, int, Decimal]] = []
    used: set[int] = set()

    for q_type, need in TYPE_PLAN:
        pool = by_type.get(q_type, [])
        chosen = random.sample(pool, min(need, len(pool)))
        picked.extend(chosen)
        used.update(item[0] for item in chosen)

    target = min(PAPER_SIZE, len(brief))
    if len(picked) < target:
        gap = target - len(picked)
        # 补足优先用客观题：简答题要逐题调模型判分，卷内过多会超出判分预算
        objective = [item for item in brief if item[0] not in used and item[1] != 4]
        chosen = random.sample(objective, min(gap, len(objective)))
        picked.extend(chosen)
        used.update(item[0] for item in chosen)

        gap = target - len(picked)
        if gap > 0:
            rest = [item for item in brief if item[0] not in used]
            picked.extend(random.sample(rest, min(gap, len(rest))))
    return picked


def build_paper(current: user, subject_id: int, db: Session) -> dict:
    subject = subject_repo.get_published(db, subject_id)
    if not subject:
        raise not_found("学科不存在")

    brief = question_repo.list_published_brief(db, subject_id)
    if not brief:
        raise api_error(40001, "该学科题池为空，请联系管理员补充题目", 409)

    # 组间按题型固定顺序（单选 → 多选 → 简答 → 判断），组内保持抽样后的随机次序：
    # 这样卷面结构稳定，且前几题来自题量最大的单选池，不会每次都一样
    picked = _sample(brief)
    picked.sort(key=lambda item: TYPE_ORDER.get(item[1], 9))
    ids = [item[0] for item in picked]

    details = {item.id: item for item in question_repo.list_by_ids(db, ids)}
    options = question_repo.options_map(db, ids)

    questions = []
    total = Decimal(0)
    for qid, _q_type, _score in picked:
        item = details.get(qid)
        if not item:
            continue
        questions.append(
            {
                "id": str(item.id),
                "type": item.type,
                "title": item.title,
                "score": float(item.score),
                # 出卷不返回 is_correct 与参考答案
                "options": [
                    {"option_key": key, "content": content}
                    for key, content, _ in options.get(qid, [])
                ],
            }
        )
        total += item.score

    return {
        "subject_id": str(subject.id),
        "subject_name": subject.name,
        "question_count": len(questions),
        "total_score": float(total),
        "questions": questions,
    }
