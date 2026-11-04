"""导入真实课程数据（435 门），按「所属学科」自动建学科并分发课程。

规则：
  - 「所属学科」含多个时取第一个作为主学科；
  - 学科不存在则自动创建；
  - 幂等：按「学科 + 课程标题」去重，重复执行只补缺失。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\import_courses.py [--dry-run]
"""

import json
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

BASE = "http://127.0.0.1:8000/api/v1"
SOURCE = Path(r"D:\BaiduNetdiskDownload\资料\4. 文档素材\4. 文档素材\课程数据文件.xlsx")

ICON_MAP = {
    "AI应用与智能体开发": "🤖",
    "AI大模型开发": "🧠",
    "AI视频与短剧创作": "🎬",
    "AI测试": "🧪",
    "AI嵌入式_机器人开发": "🔌",
    "AI运维": "🛠️",
    "AI视觉设计": "🎨",
}
DEFAULT_ICON = "📚"
TITLE_LIMIT = 255


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


def read_courses() -> list[dict]:
    book = load_workbook(SOURCE, read_only=True, data_only=True)
    rows = book.active.iter_rows(values_only=True)
    header = [str(cell).strip() if cell is not None else "" for cell in next(rows)]
    index = {key: position for position, key in enumerate(header)}

    def get(row, field: str) -> str:
        position = index.get(field)
        if position is None or position >= len(row) or row[position] is None:
            return ""
        return str(row[position]).strip()

    records = []
    for row in rows:
        if row is None or all(cell in (None, "") for cell in row):
            continue

        title = get(row, "课程名称")[:TITLE_LIMIT]
        link = get(row, "播放链接")
        if not title or not link.startswith("https://www.bilibili.com/"):
            continue

        # 多学科时取第一个作为主学科
        subject_name = get(row, "所属学科").split(",")[0].strip() or "未分类"
        try:
            duration = int(float(get(row, "时长（分钟）")))
        except ValueError:
            duration = 0

        records.append(
            {
                "subject": subject_name,
                "title": title,
                "bilibili_url": link,
                "duration_minutes": max(duration, 1),
                "source": get(row, "来源"),
            }
        )
    book.close()
    return records


def ensure_subject(token: str, name: str, cache: dict[str, str]) -> str:
    if name in cache:
        return cache[name]

    status, payload = call("GET", "/admin/subjects?page=1&page_size=100", token=token)
    for item in payload["data"]["list"]:
        cache[item["name"]] = item["id"]

    if name in cache:
        return cache[name]

    status, payload = call(
        "POST",
        "/admin/subjects",
        {
            "name": name,
            "icon": ICON_MAP.get(name, DEFAULT_ICON),
            "description": "",
            "keywords": [],
        },
        token,
    )
    if status != 201:
        raise RuntimeError(f"创建学科失败：{name} → {payload}")
    print(f"新建学科「{name}」")
    cache[name] = payload["data"]["id"]
    return cache[name]


def existing_courses(token: str, subject_id: str) -> set[str]:
    status, payload = call("GET", f"/admin/subjects/{subject_id}/courses", token=token)
    if status != 200:
        return set()
    return {item["title"] for item in payload["data"]["list"]}


def main() -> int:
    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "admin123"})
    token = (payload or {}).get("data", {}).get("access_token", "")
    if not token:
        print(f"管理员登录失败：{payload}")
        return 1

    records = read_courses()
    grouped: dict[str, list[dict]] = {}
    for item in records:
        grouped.setdefault(item["subject"], []).append(item)

    print(f"读取 {len(records)} 门课程，分属 {len(grouped)} 个学科：")
    for name, items in sorted(grouped.items(), key=lambda pair: -len(pair[1])):
        print(f"  {name}: {len(items)} 门")

    if "--dry-run" in sys.argv:
        print("（--dry-run：未写入数据库）")
        return 0

    cache: dict[str, str] = {}
    stats = Counter()
    failures: list[str] = []

    for name, items in grouped.items():
        subject_id = ensure_subject(token, name, cache)
        existing = existing_courses(token, subject_id)

        for item in items:
            if item["title"] in existing:
                stats["skipped"] += 1
                continue

            body = {
                "title": item["title"],
                "duration_minutes": item["duration_minutes"],
                "description": f"来源：{item['source']}" if item["source"] else "",
                "bilibili_url": item["bilibili_url"],
            }
            status, result = call("POST", f"/admin/subjects/{subject_id}/courses", body, token)
            if status == 201:
                stats["created"] += 1
                existing.add(item["title"])
            else:
                stats["failed"] += 1
                if len(failures) < 5:
                    failures.append(f"{item['title'][:24]}… → {result}")

    print(f"\n导入结果：新增 {stats['created']} 门，跳过重复 {stats['skipped']} 门，失败 {stats['failed']} 门")
    for line in failures:
        print(f"  失败样例：{line}")

    status, payload = call("GET", "/admin/subjects?page=1&page_size=100", token=token)
    print("\n当前学科与课程数：")
    for item in sorted(payload["data"]["list"], key=lambda row: -row["course_count"]):
        print(f"  {item['name']}: {item['course_count']} 门")

    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
