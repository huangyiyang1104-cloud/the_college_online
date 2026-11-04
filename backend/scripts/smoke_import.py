"""Excel 批量导入冒烟：解析 → 预览校验 → 确认入库 → 校验落库结果。

不依赖现成学科，脚本自建一个临时学科并在结束时清理。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\smoke_import.py
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request
import uuid
from io import BytesIO

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from openpyxl import Workbook  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
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


def upload(path: str, filename: str, content: bytes, fields: dict, token: str):
    boundary = "----yunshu" + uuid.uuid4().hex
    chunks = []
    for key, value in fields.items():
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode(
                "utf-8"
            )
        )
    chunks.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n".encode(
            "utf-8"
        )
        + content
        + b"\r\n"
    )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(chunks)

    request = urllib.request.Request(BASE + path, data=body, method="POST")
    request.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, (json.loads(raw) if raw else None)


def build_xlsx(header: list, rows: list[list]) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"OK   {label}")
    else:
        FAILED += 1
        print(f"FAIL {label} {detail}")


def main() -> int:
    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "admin123"})
    token = (payload or {}).get("data", {}).get("access_token", "")
    check("管理员登录", status == 200 and token, str(payload))
    if not token:
        return 1

    subject_name = f"导入测试-{uuid.uuid4().hex[:6]}"
    status, payload = call(
        "POST", "/admin/subjects", {"name": subject_name, "icon": "📥", "keywords": []}, token
    )
    check("准备学科", status == 201, str(payload))
    subject_id = payload["data"]["id"]

    # ---------- 课程导入：1 行合法、1 行缺课程名 ----------
    course_file = build_xlsx(
        ["课程名称", "时长（分钟）", "播放链接"],
        [
            ["导入课程 A", 30, "https://www.bilibili.com/video/BV1WWYE6LEzx"],
            ["", 30, "https://www.bilibili.com/video/BV1WWYE6LEzx"],
        ],
    )
    status, payload = upload(
        "/admin/course-imports", "courses.xlsx", course_file, {"subject_id": subject_id}, token
    )
    data = (payload or {}).get("data", {})
    check(
        "课程导入预览：2 行 1 合法 1 错误",
        status == 201
        and data.get("summary") == {"total": 2, "valid": 1, "invalid": 1}
        and data["errors"][0]["field"] == "课程名称",
        str(data)[:220],
    )
    course_job = data.get("import_id", "")

    status, payload = call(
        "PATCH", f"/admin/course-imports/{course_job}", {"status": "confirmed"}, token
    )
    check("课程导入确认入库", status == 200 and payload["data"]["imported"] == 1, str(payload))

    status, payload = call("PATCH", f"/admin/course-imports/{course_job}", {"status": "confirmed"}, token)
    check("重复确认返回 30004", status == 409 and payload["code"] == 30004, str(payload))

    status, payload = call("GET", f"/admin/subjects/{subject_id}/courses", token=token)
    titles = [item["title"] for item in payload["data"]["list"]]
    check("课程已落库且顺序接在末尾", status == 200 and "导入课程 A" in titles, str(titles))

    # ---------- 题库导入：1 道单选 + 1 道简答 ----------
    question_file = build_xlsx(
        ["题干", "题型", "正确答案", "选项A", "选项B", "选项C", "选项D"],
        [
            ["导入单选：Python 中用哪个关键字定义函数？", "单选", "B",
             "func", "def", "function", "lambda"],
            ["导入简答：简述 RAG 的基本流程。", "简答", "检索→拼接→生成", "", "", "", ""],
        ],
    )
    status, payload = upload(
        "/admin/question-imports", "questions.xlsx", question_file, {"subject_id": subject_id}, token
    )
    data = (payload or {}).get("data", {})
    check(
        "题库导入预览：2 行全部合法",
        status == 201 and data.get("summary") == {"total": 2, "valid": 2, "invalid": 0},
        str(data)[:220],
    )
    question_job = data.get("import_id", "")

    status, payload = call(
        "PATCH", f"/admin/question-imports/{question_job}", {"status": "confirmed"}, token
    )
    check("题库导入确认入库", status == 200 and payload["data"]["imported"] == 2, str(payload))

    status, payload = call("GET", f"/admin/questions?subject_id={subject_id}&page_size=20", token=token)
    items = (payload or {}).get("data", {}).get("list", [])
    single = next((item for item in items if item["type"] == 2), None)
    short = next((item for item in items if item["type"] == 4), None)
    check("单选题选项与正确项解析正确", single is not None and len(single["options"]) == 4
          and [o["option_key"] for o in single["options"] if o["is_correct"] == 1] == ["B"], str(single)[:200])
    check("简答题参考答案已写入", short is not None and short["reference_answer"] == "检索→拼接→生成",
          str(short)[:200])

    # ---------- 过期任务 ----------
    status, payload = call("GET", "/admin/imports/imp-not-exists", token=token)
    check("不存在的导入任务返回 404", status == 404, str(payload))

    # ---------- 清理 ----------
    status, payload = call("GET", f"/admin/subjects/{subject_id}/courses", token=token)
    for course in payload["data"]["list"]:
        call("DELETE", f"/admin/courses/{course['id']}", token=token)
    for item in items:
        call("DELETE", f"/admin/questions/{item['id']}", token=token)
    call("DELETE", f"/admin/subjects/{subject_id}", token=token)

    print("-" * 40)
    print(f"通过 {PASSED} 项，失败 {FAILED} 项")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
