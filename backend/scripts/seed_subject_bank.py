"""给各学科灌自拟题库（每学科 4 判断 / 8 单选 / 4 多选 / 4 简答 = 20 道）。

数据来源：scripts/bank_part1.json、bank_part2.json
幂等：按题干去重，重复执行只补缺失。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\seed_subject_bank.py [--dry-run]
"""

import json
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

BASE = "http://127.0.0.1:8000/api/v1"
HERE = Path(__file__).resolve().parent
FILES = [HERE / "bank_part1.json", HERE / "bank_part2.json"]

SCORE_MAP = {1: 5, 2: 5, 3: 10, 4: 20}


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


def load_bank() -> dict[str, dict]:
    bank: dict[str, dict] = {}
    for path in FILES:
        with path.open(encoding="utf-8") as handle:
            bank.update(json.load(handle))
    return bank


def build_payloads(subject_id: str, spec: dict) -> list[dict]:
    payloads = []

    for title, correct, analysis in spec.get("judge", []):
        payloads.append(
            {
                "subject_id": int(subject_id),
                "type": 1,
                "difficulty": 1,
                "title": title,
                "score": SCORE_MAP[1],
                "analysis": analysis,
                "options": [
                    {"option_key": "A", "content": "正确", "is_correct": 1 if correct else 0},
                    {"option_key": "B", "content": "错误", "is_correct": 0 if correct else 1},
                ],
                "tags": ["自拟"],
            }
        )

    for title, contents, answer, analysis in spec.get("single", []):
        payloads.append(
            {
                "subject_id": int(subject_id),
                "type": 2,
                "difficulty": 2,
                "title": title,
                "score": SCORE_MAP[2],
                "analysis": analysis,
                "options": [
                    {
                        "option_key": key,
                        "content": content,
                        "is_correct": 1 if key == answer.upper() else 0,
                    }
                    for key, content in zip("ABCD", contents)
                ],
                "tags": ["自拟"],
            }
        )

    for title, contents, answer, analysis in spec.get("multi", []):
        correct_keys = {item.strip().upper() for item in answer.split(",")}
        payloads.append(
            {
                "subject_id": int(subject_id),
                "type": 3,
                "difficulty": 3,
                "title": title,
                "score": SCORE_MAP[3],
                "analysis": analysis,
                "options": [
                    {
                        "option_key": key,
                        "content": content,
                        "is_correct": 1 if key in correct_keys else 0,
                    }
                    for key, content in zip("ABCD", contents)
                ],
                "tags": ["自拟"],
            }
        )

    for title, reference in spec.get("short", []):
        payloads.append(
            {
                "subject_id": int(subject_id),
                "type": 4,
                "difficulty": 3,
                "title": title,
                "score": SCORE_MAP[4],
                "reference_answer": reference,
                "analysis": "按参考要点给分，覆盖主要要点即可。",
                "options": [],
                "tags": ["自拟"],
            }
        )

    return payloads


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

    bank = load_bank()
    status, payload = call("GET", "/admin/subjects?page=1&page_size=100", token=token)
    subject_map = {item["name"]: item["id"] for item in payload["data"]["list"]}

    missing = [name for name in bank if name not in subject_map]
    if missing:
        print(f"以下学科不存在，跳过：{missing}")

    total_expected = sum(
        len(spec.get("judge", []))
        + len(spec.get("single", []))
        + len(spec.get("multi", []))
        + len(spec.get("short", []))
        for name, spec in bank.items()
        if name in subject_map
    )
    print(f"待导入 {len(bank) - len(missing)} 个学科，共 {total_expected} 道题")

    if "--dry-run" in sys.argv:
        for name, spec in bank.items():
            if name not in subject_map:
                continue
            print(
                f"  {name}: 判断 {len(spec.get('judge', []))} / 单选 {len(spec.get('single', []))}"
                f" / 多选 {len(spec.get('multi', []))} / 简答 {len(spec.get('short', []))}"
            )
        print("（--dry-run：未写入数据库）")
        return 0

    stats = Counter()
    failures: list[str] = []

    for name, spec in bank.items():
        subject_id = subject_map.get(name)
        if not subject_id:
            continue

        existing = existing_titles(token, subject_id)
        for body in build_payloads(subject_id, spec):
            if body["title"] in existing:
                stats["skipped"] += 1
                continue
            status, result = call("POST", "/admin/questions", body, token)
            if status == 201:
                stats["created"] += 1
                existing.add(body["title"])
            else:
                stats["failed"] += 1
                if len(failures) < 5:
                    failures.append(f"{name} / {body['title'][:20]}… → {result}")

    print(f"\n导入结果：新增 {stats['created']} 道，跳过重复 {stats['skipped']} 道，失败 {stats['failed']} 道")
    for line in failures:
        print(f"  失败样例：{line}")

    status, payload = call("GET", "/admin/subjects?page=1&page_size=100", token=token)
    print("\n当前学科与题量：")
    for item in payload["data"]["list"]:
        code, detail = call(
            "GET", f"/admin/questions?subject_id={item['id']}&page=1&page_size=1", token=token
        )
        count = detail["data"]["total"] if code == 200 else "?"
        print(f"  {item['name']}: 课程 {item['course_count']} · 题目 {count}")

    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
