"""按名称删除学科及其课程（走管理端接口，遵守"先删课程再删学科"的规则）。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\delete_subject.py "学科名称"
"""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"


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


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python scripts/delete_subject.py <学科名称>")
        return 1
    # 学科名可能含空格（如 "AI 全栈开发"），把参数整体拼回来
    name = " ".join(sys.argv[1:]).strip()

    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "admin123"})
    token = (payload or {}).get("data", {}).get("access_token", "")
    if not token:
        print(f"管理员登录失败：{payload}")
        return 1

    status, payload = call("GET", "/admin/subjects?page=1&page_size=100", token=token)
    matched = [item for item in payload["data"]["list"] if item["name"] == name]
    if not matched:
        print(f"没有名为「{name}」的学科（可能已删除）")
        print("当前学科：" + "、".join(item["name"] for item in payload["data"]["list"]))
        return 1

    for item in matched:
        status, payload = call("GET", f"/admin/subjects/{item['id']}/courses", token=token)
        courses = payload["data"]["list"] if status == 200 else []
        for course in courses:
            call("DELETE", f"/admin/courses/{course['id']}", token=token)
        status, payload = call("DELETE", f"/admin/subjects/{item['id']}", token=token)
        if status == 204:
            print(f"OK   已删除学科「{item['name']}」（连带 {len(courses)} 门课程："
                  + "、".join(course["title"] for course in courses) + "）")
        else:
            print(f"FAIL 删除学科失败：{payload}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
