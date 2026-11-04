"""C4 刷题冒烟：组卷比例 → 提交判分 → 错题入库 → 历史与详情。

脚本自建学科与 20 道题（4 判断 / 8 单选 / 4 多选 / 4 简答），结束后清理。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\smoke_practice.py
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.db import session_factory  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import (  # noqa: E402
    course_completion,
    exam_answer,
    exam_answer_option,
    exam_paper,
    learning_visit,
    user,
    wrong_question,
)

BASE = "http://127.0.0.1:8000/api/v1"
TEST_PHONE = "13900000003"
TEST_PASSWORD = "abc123456"
PASSED = 0
FAILED = 0


def call(method: str, path: str, body: dict | None = None, token: str = ""):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, (json.loads(raw) if raw else None)


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"OK   {label}")
    else:
        FAILED += 1
        print(f"FAIL {label} {detail}")


def setup_user() -> int:
    with session_factory() as db:
        existing = db.query(user).filter(user.phone == TEST_PHONE).one_or_none()
        if existing:
            db.query(exam_answer_option).filter(
                exam_answer_option.answer_id.in_(
                    db.query(exam_answer.id).filter(
                        exam_answer.paper_id.in_(
                            db.query(exam_paper.id).filter(exam_paper.user_id == existing.id)
                        )
                    )
                )
            ).delete(synchronize_session=False)
            db.query(exam_answer).filter(
                exam_answer.paper_id.in_(
                    db.query(exam_paper.id).filter(exam_paper.user_id == existing.id)
                )
            ).delete(synchronize_session=False)
            db.query(exam_paper).filter(exam_paper.user_id == existing.id).delete()
            db.query(wrong_question).filter(wrong_question.user_id == existing.id).delete()
            db.query(learning_visit).filter(learning_visit.user_id == existing.id).delete()
            db.query(course_completion).filter(course_completion.user_id == existing.id).delete()
            existing.password_hash = hash_password(TEST_PASSWORD)
            existing.status = 1
            db.commit()
            return existing.id
        account = user(
            phone=TEST_PHONE,
            password_hash=hash_password(TEST_PASSWORD),
            nickname="刷题学员",
            city="杭州",
            status=1,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return account.id


def cleanup(user_id: int) -> None:
    with session_factory() as db:
        paper_ids = [row[0] for row in db.query(exam_paper.id).filter(exam_paper.user_id == user_id)]
        if paper_ids:
            answer_ids = [
                row[0] for row in db.query(exam_answer.id).filter(exam_answer.paper_id.in_(paper_ids))
            ]
            if answer_ids:
                db.query(exam_answer_option).filter(
                    exam_answer_option.answer_id.in_(answer_ids)
                ).delete(synchronize_session=False)
            db.query(exam_answer).filter(exam_answer.paper_id.in_(paper_ids)).delete(
                synchronize_session=False
            )
            db.query(exam_paper).filter(exam_paper.id.in_(paper_ids)).delete(synchronize_session=False)
        db.query(wrong_question).filter(wrong_question.user_id == user_id).delete()
        account = db.get(user, user_id)
        if account:
            db.delete(account)
        db.commit()


CHOICE_KEYS = ("A", "B", "C", "D")


def seed_questions(token: str, subject_id: str) -> list[dict]:
    """造 4 判断 + 8 单选 + 4 多选 + 4 简答 = 20 题，返回题目摘要。"""
    created = []

    def post(payload: dict):
        status, body = call("POST", "/admin/questions", payload, token)
        if status != 201:
            raise RuntimeError(f"创建题目失败：{body}")
        created.append(body["data"])
        return body["data"]

    for index in range(4):
        post(
            {
                "subject_id": subject_id,
                "type": 1,
                "difficulty": 1,
                "title": f"判断 {index + 1}：Python 中列表是可变对象。",
                "score": 5,
                "options": [
                    {"option_key": "A", "content": "正确", "is_correct": 1},
                    {"option_key": "B", "content": "错误", "is_correct": 0},
                ],
                "tags": ["python"],
            }
        )

    for index in range(8):
        post(
            {
                "subject_id": subject_id,
                "type": 2,
                "difficulty": 2,
                "title": f"单选 {index + 1}：以下哪个不是 Python 内置数据类型？",
                "score": 5,
                "options": [
                    {"option_key": "A", "content": "list", "is_correct": 1},
                    {"option_key": "B", "content": "dict", "is_correct": 0},
                    {"option_key": "C", "content": "array", "is_correct": 0},
                    {"option_key": "D", "content": "tuple", "is_correct": 0},
                ],
                "tags": ["python"],
            }
        )

    for index in range(4):
        post(
            {
                "subject_id": subject_id,
                "type": 3,
                "difficulty": 3,
                "title": f"多选 {index + 1}：以下哪些属于 HTTP 方法？",
                "score": 10,
                "options": [
                    {"option_key": "A", "content": "GET", "is_correct": 1},
                    {"option_key": "B", "content": "POST", "is_correct": 1},
                    {"option_key": "C", "content": "FETCH", "is_correct": 0},
                    {"option_key": "D", "content": "SEND", "is_correct": 0},
                ],
                "tags": ["http"],
            }
        )

    for index in range(4):
        post(
            {
                "subject_id": subject_id,
                "type": 4,
                "difficulty": 3,
                "title": f"简答 {index + 1}：简述列表与元组的区别。",
                "score": 20,
                "options": [],
                "reference_answer": "列表可变，元组不可变；列表用方括号，元组用圆括号；元组可作为字典键。",
                "tags": ["python"],
            }
        )
    return created


def main() -> int:
    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "admin123"})
    admin_token = (payload or {}).get("data", {}).get("access_token", "")
    check("管理员登录", status == 200 and admin_token, str(payload))
    if not admin_token:
        return 1

    user_id = setup_user()
    status, payload = call("POST", "/auth/login", {"phone": TEST_PHONE, "password": TEST_PASSWORD})
    student_token = (payload or {}).get("data", {}).get("access_token", "")
    check("学员登录", status == 200 and student_token, str(payload))
    if not student_token:
        cleanup(user_id)
        return 1

    subject_name = f"刷题测试-{uuid.uuid4().hex[:6]}"
    status, payload = call(
        "POST", "/admin/subjects", {"name": subject_name, "icon": "📝", "keywords": []}, admin_token
    )
    check("准备学科", status == 201, str(payload))
    subject_id = payload["data"]["id"]

    questions = seed_questions(admin_token, subject_id)
    check("准备 20 道题", len(questions) == 20, str(len(questions)))

    # ---------- 组卷 ----------
    status, payload = call("GET", f"/subjects/{subject_id}/practice-paper", token=student_token)
    paper = (payload or {}).get("data", {})
    types = [item["type"] for item in paper.get("questions", [])]
    check("组卷 20 题", status == 200 and paper.get("question_count") == 20, str(paper.get("question_count")))
    check(
        "题型比例 4/8/4/4",
        types.count(1) == 4 and types.count(2) == 8 and types.count(3) == 4 and types.count(4) == 4,
        str({t: types.count(t) for t in set(types)}),
    )
    leaked = any("is_correct" in option for item in paper.get("questions", []) for option in item["options"])
    check("出卷不泄露正确选项", not leaked, "options 含 is_correct")
    check(
        "题池为空时返回 40001",
        call("GET", "/subjects/99999999/practice-paper", token=student_token)[0] == 404,
    )

    # ---------- 提交（客观全对 + 简答作答） ----------
    answers = []
    for item in paper["questions"]:
        if item["type"] == 4:
            answers.append(
                {
                    "question_id": item["id"],
                    "answer_text": "列表可变，元组不可变；列表用方括号，元组用圆括号。",
                }
            )
        elif item["type"] == 1:
            answers.append({"question_id": item["id"], "option_keys": ["A"]})
        elif item["type"] == 2:
            answers.append({"question_id": item["id"], "option_keys": ["A"]})
        else:
            answers.append({"question_id": item["id"], "option_keys": ["A", "B"]})

    status, payload = call(
        "POST", "/papers", {"subject_id": subject_id, "answers": answers}, student_token
    )
    result = (payload or {}).get("data", {})
    check("提交返回 201 且已完成判分", status == 201 and result.get("status") == 2, str(result)[:200])
    # 4×5（判断）+ 8×5（单选）+ 4×10（多选）+ 4×20（简答）= 180
    check("题目数与总分正确", result.get("question_count") == 20 and result.get("total_score") == 180.0,
          f"{result.get('question_count')} / {result.get('total_score')}")

    choice_items = [item for item in result.get("items", []) if item["question_type"] != 4]
    check(
        "客观题全部判对",
        choice_items and all(item["is_correct"] == 1 for item in choice_items),
        str([item["is_correct"] for item in choice_items]),
    )
    short_items = [item for item in result.get("items", []) if item["question_type"] == 4]
    check(
        "简答题有得分与点评",
        short_items and all(item["score_obtained"] is not None and item["ai_comment"] for item in short_items),
        str(short_items[:1])[:200],
    )
    check(
        "总分 = 各题得分之和",
        abs(result["obtained_score"] - sum(item["score_obtained"] for item in result["items"])) < 0.01,
        f"{result['obtained_score']}",
    )

    paper_id = result["id"]
    status, payload = call("GET", f"/papers/{paper_id}", token=student_token)
    check("答卷详情可回看", status == 200 and payload["data"]["id"] == paper_id, str(payload)[:160])

    # ---------- 再交一次：多选答错，验证错题入库 ----------
    before = call("GET", "/users/me", token=student_token)[1]["data"]["stats"]["wrong_count"]
    wrong_answers = []
    for item in paper["questions"]:
        if item["type"] == 3:
            wrong_answers.append({"question_id": item["id"], "option_keys": ["A"]})
        elif item["type"] == 4:
            wrong_answers.append({"question_id": item["id"], "answer_text": ""})
        else:
            wrong_answers.append({"question_id": item["id"], "option_keys": ["B"]})

    status, payload = call(
        "POST", "/papers", {"subject_id": subject_id, "answers": wrong_answers}, student_token
    )
    second = (payload or {}).get("data", {})
    check("故意答错后得分下降", status == 201 and second["obtained_score"] < result["obtained_score"],
          f"{second.get('obtained_score')}")

    after = call("GET", "/users/me", token=student_token)[1]["data"]["stats"]["wrong_count"]
    check("错题已写入错题本（4 判断 + 8 单选 + 4 多选）", after - before == 16, f"{before} → {after}")

    # ---------- 历史 ----------
    status, payload = call("GET", "/papers?page=1&page_size=10", token=student_token)
    check("历史答卷列表含 2 条", status == 200 and payload["data"]["total"] == 2, str(payload["data"]["total"]))

    status, payload = call("GET", f"/papers/{paper_id}")
    check("未登录查答卷 401", status == 401, str(payload))

    status, payload = call(
        "POST",
        "/papers",
        {"subject_id": "99999999", "answers": [{"question_id": str(questions[0]["id"]), "option_keys": ["A"]}]},
        student_token,
    )
    check("不存在的学科提交被拒（404）", status == 404, str(payload)[:160])

    # ---------- 清理 ----------
    for item in questions:
        call("DELETE", f"/admin/questions/{item['id']}", token=admin_token)
    call("DELETE", f"/admin/subjects/{subject_id}", token=admin_token)
    cleanup(user_id)

    print("-" * 40)
    print(f"通过 {PASSED} 项，失败 {FAILED} 项")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
