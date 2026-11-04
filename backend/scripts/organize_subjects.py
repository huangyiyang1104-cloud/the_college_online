"""按学科整理课程：同主题只留发布最新的一门，并按学习路径重排节点顺序。

规则来自 scripts/subject_rules.json（每个学科一套去重桶与阶段表）。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts/organize_subjects.py --dry-run
    .venv\\Scripts\\python.exe scripts/organize_subjects.py --only "AI测试"
    .venv\\Scripts\\python.exe scripts/organize_subjects.py
"""

import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

BASE = "http://127.0.0.1:8000/api/v1"
HERE = Path(__file__).resolve().parent
RULES_FILE = HERE / "subject_rules.json"

PUBDATE_CACHE: dict[str, int] = {}


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


def bvid_of(url: str) -> str:
    return url.rstrip("/").split("/")[-1].split("?")[0]


def pubdate(bvid: str) -> int:
    if bvid in PUBDATE_CACHE:
        return PUBDATE_CACHE[bvid]

    value = 0
    try:
        request = urllib.request.Request(
            f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode())
        if data.get("code") == 0:
            value = int(data["data"].get("pubdate") or 0)
    except Exception:
        value = 0

    PUBDATE_CACHE[bvid] = value
    time.sleep(0.25)
    return value


def bucket_of(title: str, rule: dict) -> str | None:
    """命中 exclude 的不参与去重；否则按去重桶顺序匹配。"""
    lowered = title.lower()
    if any(word in lowered for word in rule.get("exclude", [])):
        return None
    for name, keys in rule.get("dedup", []):
        if any(key in lowered for key in keys):
            return name
    return None


def stage_of(title: str, rule: dict) -> int:
    lowered = title.lower()
    # 项目实战与面试类永远排在最后，避免"linux运维项目"因命中 linux 被排到前面
    if any(key in lowered for key in rule.get("last_keys", [])):
        return 95
    for stage, keys in rule.get("stages", []):
        if any(key in lowered for key in keys):
            return stage
    return int(rule.get("default_stage", 90))


def pick_keep(scored: list[tuple[int, int, dict]]) -> dict:
    """保留策略：先排除明显不完整的碎片课，再在其中取发布最新的。

    scored 已按 (发布时间, 时长) 倒序。时长不足最长课 60% 的视为碎片
    （如 75 分钟的"入门"切片），否则保留最新的完整课。
    """
    max_duration = max(row[1] for row in scored)
    threshold = max_duration * 0.6
    candidates = [row for row in scored if row[1] >= threshold]
    return candidates[0][2] if candidates else scored[0][2]


def level_of(title: str) -> int:
    lowered = title.lower()
    if any(key in lowered for key in ("零基础", "入门", "基础", "小白", "从0", "全套", "速成")):
        return 0
    if any(key in lowered for key in ("进阶", "高级", "深入", "精通", "强化", "原理")):
        return 2
    return 1


def organize(name: str, subject_id: str, rule: dict, token: str, dry_run: bool) -> tuple[int, int]:
    status, payload = call("GET", f"/admin/subjects/{subject_id}/courses", token=token)
    courses = payload["data"]["list"]
    if not courses:
        print(f"\n【{name}】没有课程，跳过")
        return 0, 0

    buckets: dict[str, list[dict]] = {}
    for item in courses:
        bucket = bucket_of(item["title"], rule)
        if bucket:
            buckets.setdefault(bucket, []).append(item)

    drop_ids: list[int] = []
    groups: list[str] = []
    for group_name, items in sorted(buckets.items()):
        if len(items) < 2:
            continue

        scored = []
        for item in items:
            scored.append((pubdate(bvid_of(item["bilibili_url"])), item["duration_minutes"], item))
        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)

        keep = pick_keep(scored)
        drop = [row[2] for row in scored if row[2]["id"] != keep["id"]]
        drop_ids.extend(item["id"] for item in drop)

        groups.append(f"  [{group_name}] {len(items)} → 留「{keep['title'][:30]}」")
        if not dry_run:
            for row in scored:
                mark = "保留" if row[2]["id"] == keep["id"] else "删除"
                date = time.strftime("%Y-%m-%d", time.localtime(row[0])) if row[0] else "未知"
                groups.append(
                    f"      {mark} {date} {row[1]:>5}分 {row[2]['title'][:34]}"
                )

    group_count = len([items for items in buckets.values() if len(items) > 1])
    print(f"\n【{name}】{len(courses)} 门课，{group_count} 个重复组，待删 {len(drop_ids)} 门")
    for line in groups:
        print(line)

    if dry_run:
        return len(drop_ids), len(courses)

    removed = 0
    for course_id in drop_ids:
        status, _ = call("DELETE", f"/admin/courses/{course_id}", token=token)
        if status == 204:
            removed += 1

    status, payload = call("GET", f"/admin/subjects/{subject_id}/courses", token=token)
    remaining = payload["data"]["list"]
    remaining.sort(
        key=lambda item: (stage_of(item["title"], rule), level_of(item["title"]), -item["duration_minutes"])
    )
    order = [item["id"] for item in remaining]
    if order:
        call("PUT", f"/admin/subjects/{subject_id}/courses/order", {"course_ids": order}, token=token)

    print(f"  → 删除 {removed} 门，保留 {len(remaining)} 门，已按 {len(rule.get('stages', []))} 个阶段重排")
    for index, item in enumerate(remaining, start=1):
        print(f"     {index:3d}. {item['title'][:46]}")
    return removed, len(remaining)


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    only = None
    if "--only" in sys.argv:
        position = sys.argv.index("--only")
        if position + 1 < len(sys.argv):
            only = sys.argv[position + 1].strip()

    rules = json.loads(RULES_FILE.read_text(encoding="utf-8"))

    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "admin123"})
    token = (payload or {}).get("data", {}).get("access_token", "")
    if not token:
        print(f"管理员登录失败：{payload}")
        return 1

    status, payload = call("GET", "/admin/subjects?page=1&page_size=100", token=token)
    subjects = {item["name"]: item["id"] for item in payload["data"]["list"]}

    total_dropped = 0
    for name, rule in rules.items():
        if only and name != only:
            continue
        subject_id = subjects.get(name)
        if not subject_id:
            print(f"\n【{name}】学科不存在，跳过")
            continue
        dropped, _kept = organize(name, subject_id, rule, token, dry_run)
        total_dropped += dropped

    label = "（--dry-run：未写入数据库）" if dry_run else "（已执行删除与重排）"
    print(f"\n合计去重 {total_dropped} 门 {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
