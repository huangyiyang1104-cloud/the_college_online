"""C2 学科与课程节点图冒烟测试。

覆盖：首页聚合、学科列表/详情、节点图、推荐下一课、访问去重、点亮与取消（幂等）。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\smoke_catalog.py
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
from app.models import course_completion, learning_visit, user  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
TEST_PHONE = "13900000002"
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
            # 复用账号时先清空历史，保证统计断言从 0 开始
            db.query(learning_visit).filter(learning_visit.user_id == existing.id).delete()
            db.query(course_completion).filter(course_completion.user_id == existing.id).delete()
            existing.password_hash = hash_password(TEST_PASSWORD)
            existing.status = 1
            db.commit()
            return existing.id
        account = user(
            phone=TEST_PHONE,
            password_hash=hash_password(TEST_PASSWORD),
            nickname="节点图学员",
            city="杭州",
            status=1,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return account.id


def cleanup(user_id: int) -> None:
    with session_factory() as db:
        db.query(learning_visit).filter(learning_visit.user_id == user_id).delete()
        db.query(course_completion).filter(course_completion.user_id == user_id).delete()
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

    user_id = setup_user()
    status, payload = call("POST", "/auth/login", {"phone": TEST_PHONE, "password": TEST_PASSWORD})
    student_token = (payload or {}).get("data", {}).get("access_token", "")
    check("学员登录", status == 200 and student_token, str(payload))
    if not student_token:
        cleanup(user_id)
        return 1

    subject_name = f"节点图学科-{uuid.uuid4().hex[:6]}"
    status, payload = call(
        "POST", "/admin/subjects", {"name": subject_name, "icon": "🧪", "keywords": []}, admin_token
    )
    check("准备学科", status == 201, str(payload))
    subject_id = payload["data"]["id"]

    course_ids = []
    for index in range(2):
        status, payload = call(
            "POST",
            f"/admin/subjects/{subject_id}/courses",
            {
                "title": f"节点课程 {index + 1}",
                "duration_minutes": 30,
                "bilibili_url": "https://www.bilibili.com/video/BV1WWYE6LEzx",
            },
            admin_token,
        )
        check(f"准备课程 {index + 1}", status == 201, str(payload))
        course_ids.append(payload["data"]["id"])

    status, payload = call("GET", "/home", token=student_token)
    subjects = (payload or {}).get("data", {}).get("subjects", [])
    target = next((item for item in subjects if item["id"] == subject_id), None)
    check(
        "首页含该学科且带进度与下一课",
        status == 200
        and target is not None
        and target["course_count"] == 2
        and target["completed_count"] == 0
        and target["next_course"]["id"] == course_ids[0],
        str(target),
    )

    status, payload = call("GET", "/subjects?page=1&page_size=50", token=student_token)
    ids = [item["id"] for item in (payload or {}).get("data", {}).get("list", [])]
    check("学科列表包含新学科", status == 200 and subject_id in ids, str(payload)[:200])

    status, payload = call("GET", f"/subjects/{subject_id}", token=student_token)
    detail = (payload or {}).get("data", {})
    check(
        "学科详情节点数正确",
        status == 200 and len(detail.get("nodes", [])) == 2 and detail["progress_percent"] == 0,
        str(detail)[:200],
    )
    check("推荐下一课为第一节", detail.get("recommended_course_id") == course_ids[0], str(detail.get("recommended_course_id")))

    status, payload = call("POST", f"/courses/{course_ids[0]}/visits", token=student_token)
    check("首次访问返回 201", status == 201 and payload["data"]["id"], str(payload))
    visit_id = payload["data"]["id"]

    status, payload = call("POST", f"/courses/{course_ids[0]}/visits", token=student_token)
    check(
        "同日重复访问返回 200 且不新增",
        status == 200 and payload["data"]["id"] == visit_id,
        str(payload),
    )

    status, payload = call("GET", "/home", token=student_token)
    recent = (payload or {}).get("data", {}).get("recent_visits", [])
    check(
        "首页最近学习有 1 条",
        status == 200 and len(recent) == 1 and recent[0]["course_id"] == course_ids[0],
        str(recent),
    )

    status, payload = call("PUT", f"/courses/{course_ids[0]}/completion", token=student_token)
    first_completed_at = (payload or {}).get("data", {}).get("completed_at")
    check("点亮节点", status == 200 and first_completed_at, str(payload))

    status, payload = call("PUT", f"/courses/{course_ids[0]}/completion", token=student_token)
    check(
        "重复点亮幂等（时间不变）",
        status == 200 and payload["data"]["completed_at"] == first_completed_at,
        str(payload),
    )

    status, payload = call("GET", f"/subjects/{subject_id}", token=student_token)
    detail = (payload or {}).get("data", {})
    check(
        "点亮后进度 50% 且推荐下一课后移",
        detail.get("completed_count") == 1
        and detail.get("progress_percent") == 50
        and detail.get("recommended_course_id") == course_ids[1],
        str(detail)[:200],
    )
    check(
        "节点回显点亮状态",
        detail["nodes"][0]["is_completed"] is True and detail["nodes"][1]["is_completed"] is False,
        str(detail["nodes"])[:200],
    )

    # ---- C3 学习记录 ----
    status, payload = call("GET", "/learning-records", token=student_token)
    records = (payload or {}).get("data", {})
    first_record = (records.get("list") or [{}])[0]
    check(
        "学习记录列表含本次访问且标记已点亮",
        status == 200
        and records.get("total") == 1
        and first_record.get("course_id") == course_ids[0]
        and first_record.get("is_completed") is True,
        str(records)[:200],
    )

    status, payload = call(
        "GET", f"/learning-records?subject_id={subject_id}", token=student_token
    )
    check("按学科筛选学习记录", status == 200 and payload["data"]["total"] == 1, str(payload)[:160])

    status, payload = call("GET", "/learning-records/summary", token=student_token)
    stats = (payload or {}).get("data", {})
    check(
        "学习统计：访问 1 / 点亮 1 / 学科 1",
        status == 200
        and stats == {"visited_count": 1, "completed_count": 1, "subject_count": 1},
        str(stats),
    )

    status, payload = call("DELETE", f"/courses/{course_ids[0]}/completion", token=student_token)
    check("取消点亮返回 204", status == 204, str(payload))

    status, payload = call("GET", "/learning-records/summary", token=student_token)
    stats = (payload or {}).get("data", {})
    check(
        "取消点亮后 completed 归零、访问记录保留",
        stats.get("completed_count") == 0 and stats.get("visited_count") == 1,
        str(stats),
    )

    status, payload = call("GET", f"/subjects/{subject_id}", token=student_token)
    detail = (payload or {}).get("data", {})
    check(
        "取消后进度回到 0",
        detail.get("completed_count") == 0 and detail.get("recommended_course_id") == course_ids[0],
        str(detail)[:200],
    )

    status, payload = call("PUT", "/courses/99999999/completion", token=student_token)
    check("不存在的课程返回 404", status == 404, str(payload))

    status, payload = call("GET", "/subjects/99999999", token=student_token)
    check("不存在的学科返回 404", status == 404, str(payload))

    status, payload = call("GET", "/subjects", token="")
    check("未登录访问学科列表 401", status == 401, str(payload))

    for course_id in course_ids:
        call("DELETE", f"/admin/courses/{course_id}", token=admin_token)
    call("DELETE", f"/admin/subjects/{subject_id}", token=admin_token)
    cleanup(user_id)

    print("-" * 40)
    print(f"通过 {PASSED} 项，失败 {FAILED} 项")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
