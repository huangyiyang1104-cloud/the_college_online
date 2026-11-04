"""导入真实题库（三个 xlsx），按标签拆分到不同学科。

规则（已确认）：
  - 标签含 JavaEE / JavaSE 的 303 道 → 新建「Java 开发」学科
  - 其余（python核心 / Maven / HTML 等 10 道）→「AI全栈开发」学科
  - 幂等：按题干去重，重复执行只补缺失

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\import_question_bank.py
"""

import json
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

BASE = "http://127.0.0.1:8000/api/v1"
SOURCE = Path(r"D:\BaiduNetdiskDownload\资料\4. 文档素材\4. 文档素材")

FILES = [
    "题库管理-测试数据(单选).xlsx",
    "题库管理-测试数据(多选).xlsx",
    "题库管理-测试数据(简答).xlsx",
]

JAVA_SUBJECT = "Java 开发"
PYTHON_SUBJECT = "AI全栈开发"

TYPE_MAP = {"判断": 1, "判断题": 1, "单选": 2, "单选题": 2, "多选": 3, "多选题": 3, "简答": 4, "简答题": 4}
DIFFICULTY_MAP = {"简单": 1, "中等": 2, "困难": 3, "难": 3}
SCORE_MAP = {1: 5, 2: 5, 3: 10, 4: 20}
JAVA_TAGS = ("javaee", "javase")

OPTION_CONTENT_LIMIT = 512
TEXT_LIMIT = 20000


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


def read_all() -> list[dict]:
    """读取三个文件，统一成待创建结构。"""
    records: list[dict] = []
    for name in FILES:
        book = load_workbook(SOURCE / name, read_only=True, data_only=True)
        rows = book.active.iter_rows(values_only=True)
        header = [str(cell).strip() if cell is not None else "" for cell in next(rows)]
        index = {key: position for position, key in enumerate(header)}

        for row in rows:
            if row is None or all(cell in (None, "") for cell in row):
                continue

            def get(field: str) -> str:
                position = index.get(field)
                if position is None or position >= len(row) or row[position] is None:
                    return ""
                return str(row[position]).strip()

            q_type = TYPE_MAP.get(get("题型"))
            title = get("题干")
            if not q_type or not title:
                continue

            tags = [item.strip() for item in get("标签").replace("，", ",").split(",") if item.strip()]
            answer = get("正确答案")

            options = []
            if q_type != 4:
                for letter in "ABCDEF":
                    content = get(f"选项{letter}")
                    if not content:
                        continue
                    options.append(
                        {
                            "option_key": letter,
                            "content": content[:OPTION_CONTENT_LIMIT],
                            "is_correct": 1 if letter in answer.upper() else 0,
                        }
                    )
                if not options:
                    continue

            lowered = [tag.lower() for tag in tags]
            is_java = any(keyword in tag for tag in lowered for keyword in JAVA_TAGS)

            records.append(
                {
                    "bucket": "java" if is_java else "python",
                    "type": q_type,
                    "difficulty": DIFFICULTY_MAP.get(get("难度"), 2),
                    "category": get("分类")[:64],
                    "title": title[:TEXT_LIMIT],
                    "score": SCORE_MAP[q_type],
                    "options": options,
                    "reference_answer": answer[:TEXT_LIMIT] if q_type == 4 else None,
                    "analysis": get("解析")[:TEXT_LIMIT] or None,
                    "tags": tags[:10],
                }
            )
        book.close()
    return records


def ensure_subject(token: str, name: str) -> str:
    status, payload = call("GET", "/admin/subjects?page=1&page_size=100", token=token)
    for item in payload["data"]["list"]:
        if item["name"] == name:
            return item["id"]

    status, payload = call(
        "POST",
        "/admin/subjects",
        {"name": name, "icon": "☕" if "Java" in name else "🧠", "description": "", "keywords": []},
        token,
    )
    if status != 201:
        raise RuntimeError(f"创建学科失败：{payload}")
    print(f"新建学科「{name}」")
    return payload["data"]["id"]


def existing_titles(token: str, subject_id: str) -> set[str]:
    titles: set[str] = set()
    page = 1
    while True:
        status, payload = call(
            "GET", f"/admin/questions?subject_id={subject_id}&page={page}&page_size=100", token=token
        )
        if status != 200:
            break
        data = payload["data"]
        titles.update(item["title"] for item in data["list"])
        if page * data["page_size"] >= data["total"]:
            break
        page += 1
    return titles


def main() -> int:
    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "admin123"})
    token = (payload or {}).get("data", {}).get("access_token", "")
    if not token:
        print(f"管理员登录失败：{payload}")
        return 1

    records = read_all()
    buckets = Counter(item["bucket"] for item in records)
    print(f"读取 {len(records)} 道题：Java {buckets['java']} / Python {buckets['python']}")

    if "--dry-run" in sys.argv:
        for bucket in ("java", "python"):
            items = [item for item in records if item["bucket"] == bucket]
            types = Counter(item["type"] for item in items)
            print(
                f"  {bucket}: 共 {len(items)} 道"
                f"（判断 {types[1]} / 单选 {types[2]} / 多选 {types[3]} / 简答 {types[4]}）"
            )
            for sample in items[:2]:
                print(f"    样例：[{sample['type']}] {sample['title'][:40]}… 选项 {len(sample['options'])} 个")
        print("（--dry-run：未写入数据库）")
        return 0

    targets = {
        "java": ensure_subject(token, JAVA_SUBJECT),
        "python": ensure_subject(token, PYTHON_SUBJECT),
    }

    stats = Counter()
    failures: list[str] = []

    for bucket, subject_id in targets.items():
        existing = existing_titles(token, subject_id)
        items = [item for item in records if item["bucket"] == bucket]

        for item in items:
            if item["title"] in existing:
                stats["skipped"] += 1
                continue

            body = {
                "subject_id": int(subject_id),
                "type": item["type"],
                "difficulty": item["difficulty"],
                "category": item["category"],
                "title": item["title"],
                "score": item["score"],
                "options": item["options"],
                "reference_answer": item["reference_answer"],
                "analysis": item["analysis"],
                "tags": item["tags"],
            }
            status, result = call("POST", "/admin/questions", body, token)
            if status == 201:
                stats["created"] += 1
                existing.add(item["title"])
            else:
                stats["failed"] += 1
                if len(failures) < 5:
                    failures.append(f"{item['title'][:30]}… → {result}")

    print(f"\n导入结果：新增 {stats['created']} 道，跳过重复 {stats['skipped']} 道，失败 {stats['failed']} 道")
    for line in failures:
        print(f"  失败样例：{line}")

    for label, subject_id in targets.items():
        status, payload = call(
            "GET", f"/admin/questions?subject_id={subject_id}&page=1&page_size=1", token=token
        )
        total = payload["data"]["total"] if status == 200 else "?"
        name = JAVA_SUBJECT if label == "java" else PYTHON_SUBJECT
        print(f"  「{name}」题池共 {total} 道")

    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
