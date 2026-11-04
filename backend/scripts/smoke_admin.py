"""管理端接口冒烟测试：按业务流程依次调用，校验状态码与关键字段。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\smoke_admin.py
"""

import json
import sys
import urllib.error
import urllib.request
import uuid

BASE = "http://127.0.0.1:8000/api/v1"
TOKEN = ""
PASSED = 0
FAILED = 0


def call(method: str, path: str, body: dict | None = None, token: str = "", expect: int = 200):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
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


def main() -> int:
    global TOKEN

    status, payload = call("GET", "/health")
    check("健康检查", status == 200 and payload["code"] == 0, str(payload))

    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "admin123"})
    check("管理员登录", status == 200 and payload["data"].get("access_token"), str(payload))
    if status != 200:
        return 1
    TOKEN = payload["data"]["access_token"]

    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "wrongpass"})
    check(
        "错误密码返回 401 + 20003 + 中文提示",
        status == 401 and payload["code"] == 20003 and payload["message"] == "账号或密码错误",
        str(payload),
    )

    status, payload = call("GET", "/admin/auth/me", token=TOKEN)
    check("当前账号", status == 200 and payload["data"]["username"] == "admin", str(payload))

    status, payload = call("GET", "/admin/dashboard/summary", token=TOKEN)
    check(
        "看板摘要",
        status == 200 and "register_trend" in payload["data"] and len(payload["data"]["register_trend"]) == 7,
        str(payload),
    )

    name = f"冒烟学科-{uuid.uuid4().hex[:6]}"
    status, payload = call(
        "POST",
        "/admin/subjects",
        {"name": name, "icon": "🧪", "description": "冒烟测试学科", "keywords": ["python", "gil"]},
        TOKEN,
        201,
    )
    check("新增学科", status == 201 and payload["data"]["keywords"] == ["python", "gil"], str(payload))
    subject_id = payload["data"]["id"]

    status, payload = call("GET", f"/admin/subjects/{subject_id}", token=TOKEN)
    check("学科详情", status == 200 and payload["data"]["course_count"] == 0, str(payload))

    status, payload = call(
        "PATCH", f"/admin/subjects/{subject_id}", {"description": "改过的简介", "keywords": ["python"]}, TOKEN
    )
    check("编辑学科", status == 200 and payload["data"]["description"] == "改过的简介", str(payload))

    course_ids = []
    for index in range(2):
        status, payload = call(
            "POST",
            f"/admin/subjects/{subject_id}/courses",
            {
                "title": f"冒烟课程 {index + 1}",
                "duration_minutes": 30 + index,
                "bilibili_url": "https://www.bilibili.com/video/BV1WWYE6LEzx",
                "description": "冒烟课程",
            },
            TOKEN,
            201,
        )
        check(f"新增课程 {index + 1}", status == 201, str(payload))
        if status == 201:
            course_ids.append(payload["data"]["id"])

    status, payload = call("POST", f"/admin/subjects/{subject_id}/courses", {
        "title": "非法链接课程",
        "duration_minutes": 10,
        "bilibili_url": "https://example.com/x",
    }, TOKEN)
    check("非 B 站链接被拒", status == 400, str(payload))

    status, payload = call("GET", f"/admin/subjects/{subject_id}/courses", token=TOKEN)
    check("课程列表", status == 200 and payload["data"]["total"] == 2, str(payload))

    status, payload = call(
        "PUT", f"/admin/subjects/{subject_id}/courses/order", {"course_ids": list(reversed(course_ids))}, TOKEN
    )
    check("课程排序", status == 200 and payload["data"]["updated"] == 2, str(payload))

    status, payload = call("DELETE", f"/admin/subjects/{subject_id}", token=TOKEN)
    check("学科有课程时禁止删除", status == 409 and payload["code"] == 30001, str(payload))

    status, payload = call(
        "POST",
        "/admin/questions",
        {
            "subject_id": subject_id,
            "type": 2,
            "difficulty": 1,
            "category": "冒烟",
            "title": "下列哪种结构适合做键值映射查找？",
            "score": 10,
            "options": [
                {"option_key": "A", "content": "list", "is_correct": 0},
                {"option_key": "B", "content": "dict", "is_correct": 1},
            ],
            "analysis": "dict 基于哈希表",
            "tags": ["python"],
        },
        TOKEN,
        201,
    )
    check("新增单选题", status == 201 and len(payload["data"]["options"]) == 2, str(payload))
    question_id = payload["data"]["id"]

    status, payload = call(
        "POST",
        "/admin/questions",
        {"subject_id": subject_id, "type": 4, "title": "简述 GIL", "score": 20},
        TOKEN,
    )
    check("简答题缺参考答案被拒", status == 400, str(payload))

    status, payload = call("GET", f"/admin/questions?subject_id={subject_id}", token=TOKEN)
    check("题库列表", status == 200 and payload["data"]["total"] == 1, str(payload))

    status, payload = call("PATCH", f"/admin/questions/{question_id}", {"analysis": "补充解析"}, TOKEN)
    check("编辑题目", status == 200 and payload["data"]["analysis"] == "补充解析", str(payload))

    username = f"ops{uuid.uuid4().hex[:6]}"
    status, payload = call("POST", "/admin/users", {"username": username, "password": "abc123456", "role": 2}, TOKEN, 201)
    check("新增后台账号", status == 201 and payload["data"]["role"] == 2, str(payload))
    admin_id = payload["data"]["id"]

    status, payload = call("PATCH", f"/admin/users/{admin_id}", {"status": 0}, TOKEN)
    check("停用后台账号", status == 200 and payload["data"]["status"] == 0, str(payload))

    status, payload = call("DELETE", f"/admin/users/{admin_id}", token=TOKEN)
    check("删除后台账号", status == 204, str(payload))

    status, payload = call("GET", "/admin/students", token=TOKEN)
    check("学员列表", status == 200 and "completed_course_count" in (payload["data"]["list"][0] if payload["data"]["list"] else {"completed_course_count": 0}), str(payload))

    status, payload = call("GET", "/admin/operation-logs?page_size=5", token=TOKEN)
    check("操作日志", status == 200 and payload["data"]["total"] > 0, str(payload))

    status, payload = call("GET", "/admin/interview-docs", token=TOKEN)
    check("资料库列表", status == 200, str(payload))

    status, payload = call("GET", "/admin/retrieval-tests?query=agent", token=TOKEN)
    # 资料库已有切片，这里应能命中；断言结构而非空结果
    hits = (payload or {}).get("data", {}).get("items") or []
    check(
        "检索测试返回命中切片",
        status == 200 and len(hits) > 0 and bool(hits[0].get("content")),
        str(payload)[:200],
    )

    for course_id in course_ids:
        call("DELETE", f"/admin/courses/{course_id}", token=TOKEN)
    status, payload = call("DELETE", f"/admin/subjects/{subject_id}", token=TOKEN)
    check("课程清空后删除学科", status == 204, str(payload))
    call("DELETE", f"/admin/questions/{question_id}", token=TOKEN)

    print("-" * 40)
    print(f"通过 {PASSED} 项，失败 {FAILED} 项")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
