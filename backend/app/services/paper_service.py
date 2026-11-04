"""C4 刷题：整卷提交、判分与答卷查询。

判分口径（已确认）：
  - 客观题即时判分，多选必须完全一致才得分，否则 0 分；
  - 简答题在**请求内**等待大模型判分，整体预算 25 秒；
    预算用尽或模型不可用时按关键词重合度兜底，保证一定返回结果；
  - 客观错题写入错题本（简答题不写）。
"""

import time
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.errors import api_error, not_found
from app.integrations import llm
from app.models import exam_answer, exam_answer_option, exam_paper, user, wrong_question
from app.repositories import exam_repo, question_repo, subject_repo, wrong_repo

TYPE_SHORT_ANSWER = 4
SCORING_BUDGET_SECONDS = 25


def _dt(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else None


def _money(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _detail(paper: exam_paper, db: Session) -> dict:
    answers = exam_repo.answers_by_paper(db, paper.id)
    options = exam_repo.answer_options_map(db, [item.id for item in answers])
    names = exam_repo.subject_name_map(db, [paper.subject_id])

    # 判分已完成才展示正确选项与参考答案（判分中只回作答）
    question_ids = [item.question_id for item in answers]
    correct_options = question_repo.options_map(db, question_ids) if paper.status == 2 else {}

    items = []
    pending = 0
    for index, answer in enumerate(answers, start=1):
        if answer.score_obtained is None:
            pending += 1

        option_rows = correct_options.get(answer.question_id, [])
        items.append(
            {
                "question_index": index,
                "question_id": str(answer.question_id),
                "question_type": answer.question_type,
                "title": answer.question_title,
                "score_max": _money(answer.score_max),
                "score_obtained": _money(answer.score_obtained),
                "is_correct": answer.is_correct,
                "my_option_keys": [row.option_key for row in options.get(answer.id, [])],
                "correct_option_keys": [key for key, _c, is_correct in option_rows if is_correct == 1],
                "options": [
                    {"option_key": key, "content": content, "is_correct": is_correct}
                    for key, content, is_correct in option_rows
                ],
                "answer_text": answer.answer_text,
                "reference_answer": answer.reference_answer,
                "ai_comment": answer.ai_comment,
            }
        )

    return {
        "id": str(paper.id),
        "subject_id": str(paper.subject_id),
        "subject_name": names.get(paper.subject_id, ""),
        "status": paper.status,
        "question_count": paper.question_count,
        "total_score": _money(paper.total_score),
        "obtained_score": _money(paper.obtained_score),
        "pending_count": pending,
        "submitted_at": _dt(paper.submitted_at),
        "items": items,
    }


def get_paper(current: user, paper_id: int, db: Session) -> dict:
    paper = exam_repo.get_paper(db, paper_id, current.id)
    if not paper:
        raise not_found("答卷不存在")
    return _detail(paper, db)


def list_papers(
    current: user, subject_id: int | None, page: int, page_size: int, db: Session
) -> tuple[list[dict], int]:
    papers, total = exam_repo.paginate_papers(
        db, current.id, subject_id, (page - 1) * page_size, page_size
    )
    names = exam_repo.subject_name_map(db, list({item.subject_id for item in papers}))
    rows = [
        {
            "id": str(item.id),
            "subject_id": str(item.subject_id),
            "subject_name": names.get(item.subject_id, ""),
            "question_count": item.question_count,
            "total_score": _money(item.total_score),
            "obtained_score": _money(item.obtained_score),
            "status": item.status,
            "submitted_at": _dt(item.submitted_at),
        }
        for item in papers
    ]
    return rows, total


def _grade_choice(correct_keys: list[str], chosen_keys: list[str]) -> bool:
    """多选必须完全一致；单选/判断同理；空作答算错。"""
    if not correct_keys or not chosen_keys:
        return False
    return set(correct_keys) == set(chosen_keys)


def submit(current: user, subject_id: int, answers: list, db: Session) -> dict:
    if not subject_repo.get_published(db, subject_id):
        raise not_found("学科不存在")

    question_ids = [int(item.question_id) for item in answers]
    details = {item.id: item for item in question_repo.list_by_ids(db, question_ids)}

    for question_id in question_ids:
        item = details.get(question_id)
        if not item or item.subject_id != subject_id:
            raise api_error(40003, "题目不属于该学科或已下架", 400)

    options = question_repo.options_map(db, question_ids)
    total_score = sum((details[qid].score for qid in question_ids), Decimal(0))

    paper = exam_repo.add_paper(
        db,
        exam_paper(
            user_id=current.id,
            subject_id=subject_id,
            question_count=len(question_ids),
            total_score=total_score,
            status=1,
            submitted_at=utcnow(),
        ),
    )

    deadline = time.monotonic() + SCORING_BUDGET_SECONDS
    obtained = Decimal(0)
    wrong_ids: list[int] = []

    for entry in answers:
        item = details[int(entry.question_id)]
        answer_row = exam_repo.add_answer(
            db,
            exam_answer(
                paper_id=paper.id,
                question_id=item.id,
                question_title=item.title,
                question_type=item.type,
                score_max=item.score,
                reference_answer=item.reference_answer if item.type == TYPE_SHORT_ANSWER else None,
            ),
        )

        if item.type == TYPE_SHORT_ANSWER:
            text = (entry.answer_text or "").strip()
            answer_row.answer_text = text

            if not text:
                ratio, comment = Decimal(0), "未作答"
            else:
                remain = deadline - time.monotonic()
                result = (
                    llm.score_short_answer(item.title, item.reference_answer or "", text, remain)
                    if remain > 2
                    else None
                )
                ratio, comment = result if result else llm.fallback_score(
                    item.reference_answer or "", text
                )

            score = (item.score * ratio).quantize(Decimal("0.01"))
            answer_row.score_obtained = score
            answer_row.ai_comment = comment
            answer_row.judged_at = utcnow()
            obtained += score
            continue

        correct_keys = [key for key, _content, is_correct in options.get(item.id, []) if is_correct == 1]
        chosen_keys = [key.upper() for key in (entry.option_keys or [])]
        is_correct = _grade_choice(correct_keys, chosen_keys)
        score = item.score if is_correct else Decimal(0)

        answer_row.is_correct = 1 if is_correct else 0
        answer_row.score_obtained = score
        answer_row.judged_at = utcnow()
        obtained += score
        if not is_correct:
            wrong_ids.append(item.id)

        content_map = {key: content for key, content, _ in options.get(item.id, [])}
        exam_repo.add_answer_options(
            db,
            [
                exam_answer_option(
                    answer_id=answer_row.id,
                    option_key=key,
                    option_content=content_map.get(key, ""),
                    is_correct=1 if key in correct_keys else 0,
                )
                for key in chosen_keys
            ],
        )

    now = utcnow()
    for question_id in wrong_ids:
        existing = wrong_repo.get(db, current.id, question_id)
        if existing:
            wrong_repo.touch(db, existing, now)
        else:
            wrong_repo.add(
                db,
                wrong_question(
                    user_id=current.id,
                    question_id=question_id,
                    wrong_times=1,
                    last_wrong_at=now,
                ),
            )

    paper.status = 2
    paper.obtained_score = obtained
    paper.updated_at = now

    db.commit()
    db.refresh(paper)
    return _detail(paper, db)
