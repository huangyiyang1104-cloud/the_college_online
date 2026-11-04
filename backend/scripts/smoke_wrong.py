"""C5 错题本冒烟：答错入本 → 列表脱敏 → 重做答对移除 → 答错累加 → 手动移除。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\smoke_wrong.py
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
TEST_PHONE = "13900000004"
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


def reset_user() -> int:
    with session_factory() as db:
        existing = db.query(user).filter(user.phone == TEST_PHONE).one_or_none()
        if not existing:
            account = user(
                phone=TEST_PHONE,
                password_hash=hash_password(TEST_PASSWORD),
                nickname="错题学员",
                city="杭州",
                status=1,
            )
            db.add(account)
            db.commit()
            db.refresh(account)
            return account.id

        paper_ids = [
            row[0] for row in db.query(exam_paper.id).filter(exam_paper.user_id == existing.id)
        ]
        if paper_ids:
            answer_ids = [
                row[0]
                for row in db.query(exam_answer.id).filter(exam_answer.paper_id.in_(paper_ids))
            ]
            if answer_ids:
                db.query(exam_answer_option).filter(
                    exam_answer_option.answer_id.in_(answer_ids)
                ).delete(synchronize_session=False)
            db.query(exam_answer).filter(exam_answer.paper_id.in_(paper_ids)).delete(
                synchronize_session=False
            )
            db.query(exam_paper).filter(exam_paper.id.in_(paper_ids)).delete(
                synchronize_session=False
            )
        db.query(wrong_question).filter(wrong_question.user_id == existing.id).delete()
        db.query(learning_visit).filter(learning_visit.user_id == existing.id).delete()
        db.query(course_completion).filter(course_completion.user_id == existing.id).delete()
        existing.password_hash = hash_password(TEST_PASSWORD)
        existing.status = 1
        db.commit()
        return existing.id


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


def main() -> int:
    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "admin123"})
    admin_token = (payload or {}).get("data", {}).get("access_token", "")
    check("管理员登录", status == 200 and admin_token, str(payload))
    if not admin_token:
        return 1

    user_id = reset_user()
    status, payload = call("POST", "/auth/login", {"phone": TEST_PHONE, "password": TEST_PASSWORD})
    student_token = (payload or {}).get("data", {}).get("access_token", "")
    check("学员登录", status == 200 and student_token, str(payload))
    if not student_token:
        cleanup(user_id)
        return 1

    subject_name = f"错题测试-{uuid.uuid4().hex[:6]}"
    status, payload = call(
        "POST", "/admin/subjects", {"name": subject_name, "icon": "🧾", "keywords": []}, admin_token
    )
    check("准备学科", status == 201, str(payload))
    subject_id = payload["data"]["id"]

    created = []

    def create_question(payload: dict) -> dict:
        status, body = call("POST", "/admin/questions", payload, admin_token)
        if status != 201:
            raise RuntimeError(f"创建题目失败：{body}")
        created.append(body["data"])
        return body["data"]

    single = create_question(
        {
            "subject_id": subject_id,
            "type": 2,
            "difficulty": 2,
            "title": "单选：Python 中用哪个关键字定义函数？",
            "score": 10,
            "analysis": "def 是定义函数的关键字。",
            "options": [
                {"option_key": "A", "content": "def", "is_correct": 1},
                {"option_key": "B", "content": "func", "is_correct": 0},
            ],
        }
    )
    multi = create_question(
        {
            "subject_id": subject_id,
            "type": 3,
            "difficulty": 3,
            "title": "多选：以下哪些是不可变类型？",
            "score": 10,
            "analysis": "str 与 tuple 不可变。",
            "options": [
                {"option_key": "A", "content": "str", "is_correct": 1},
                {"option_key": "B", "content": "list", "is_correct": 0},
                {"option_key": "C", "content": "tuple", "is_correct": 1},
            ],
        }
    )
    create_question(
        {
            "subject_id": subject_id,
            "type": 4,
            "difficulty": 3,
            "title": "简答：简述 GIL 的作用。",
            "score": 20,
            "reference_answer": "全局解释器锁，保证同一时刻只有一个线程执行字节码。",
            "options": [],
        }
    )

    # ---------- 全部答错 → 进错题本 ----------
    status, payload = call(
        "POST",
        "/papers",
        {
            "subject_id": subject_id,
            "answers": [
                {"question_id": single["id"], "option_keys": ["B"]},
                {"question_id": multi["id"], "option_keys": ["B"]},
            ],
        },
        student_token,
    )
    check("提交 2 道客观题并判分", status == 201 and payload["data"]["obtained_score"] == 0.0, str(payload)[:160])

    status, payload = call("GET", "/wrong-questions?page=1&page_size=10", token=student_token)
    data = (payload or {}).get("data", {})
    rows = data.get("list", [])
    check("错题本收录 2 道客观题（不含简答）", status == 200 and data.get("total") == 2, str(data.get("total")))
    leaked = any("is_correct" in option for row in rows for option in row["options"])
    check("列表不泄露正确答案", not leaked, "options 含 is_correct")
    check(
        "列表含学科名与错误次数",
        rows and rows[0]["subject_name"] == subject_name and rows[0]["wrong_times"] == 1,
        str(rows[:1])[:200],
    )

    status, payload = call("GET", f"/wrong-questions?subject_id={subject_id}", token=student_token)
    check("按学科筛选", status == 200 and payload["data"]["total"] == 2, str(payload["data"]["total"]))

    # ---------- 重做答对 → 移出 ----------
    status, payload = call(
        "POST", f"/wrong-questions/{single['id']}/attempts", {"option_keys": ["A"]}, student_token
    )
    result = (payload or {}).get("data", {})
    check(
        "重做答对：返回正确项与解析并移除",
        status == 200
        and result.get("is_correct") == 1
        and result.get("correct_option_keys") == ["A"]
        and result.get("removed") is True
        and "def" in result.get("analysis", ""),
        str(result),
    )

    status, payload = call("GET", "/wrong-questions", token=student_token)
    check("答对后错题本剩 1 道", payload["data"]["total"] == 1, str(payload["data"]["total"]))

    # ---------- 重做答错 → 次数累加 ----------
    status, payload = call(
        "POST", f"/wrong-questions/{multi['id']}/attempts", {"option_keys": ["A"]}, student_token
    )
    result = (payload or {}).get("data", {})
    check(
        "重做答错：不通过且不移除",
        status == 200 and result.get("is_correct") == 0 and result.get("removed") is False,
        str(result),
    )
    check("答错返回完整正确项", result.get("correct_option_keys") == ["A", "C"], str(result))

    status, payload = call("GET", "/wrong-questions", token=student_token)
    check("答错后错误次数累加为 2", payload["data"]["list"][0]["wrong_times"] == 2, str(payload["data"]["list"])[:160])

    # ---------- 手动移除（幂等） ----------
    status, payload = call("DELETE", f"/wrong-questions/{multi['id']}", token=student_token)
    check("手动移除返回 204", status == 204, str(payload))
    status, payload = call("DELETE", f"/wrong-questions/{multi['id']}", token=student_token)
    check("重复移除仍返回 204（幂等）", status == 204, str(payload))
    status, payload = call("GET", "/wrong-questions", token=student_token)
    check("移除后错题本为空", payload["data"]["total"] == 0, str(payload["data"]["total"]))

    status, payload = call(
        "POST", "/wrong-questions/99999999/attempts", {"option_keys": ["A"]}, student_token
    )
    check("重做不存在的题返回 404", status == 404, str(payload)[:160])

    status, payload = call("GET", "/wrong-questions")
    check("未登录访问 401", status == 401, str(payload)[:120])

    # ---------- 清理 ----------
    for item in created:
        call("DELETE", f"/admin/questions/{item['id']}", token=admin_token)
    call("DELETE", f"/admin/subjects/{subject_id}", token=admin_token)
    cleanup(user_id)

    print("-" * 40)
    print(f"通过 {PASSED} 项，失败 {FAILED} 项")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
