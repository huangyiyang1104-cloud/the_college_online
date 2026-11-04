"""C6 学科面试冒烟测试：配额 → 发起出题 → 作答评分 → 追问 → 结束 → 记录。

会真实调用 embedding 与 LLM（出题一次、评分两次、追问一次），耗时约 1-2 分钟。
跑完会清理本次会话与当日配额计数，可重复执行。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\smoke_interview.py
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.cache import redis_client  # noqa: E402
from app.core.config import settings_cache  # noqa: E402
from app.core.db import session_factory  # noqa: E402
from app.models import interview_question, interview_session, user  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
PHONE = "19880836572"
PASSWORD = "Abc123456"
PASSED = 0
FAILED = 0


def call(method: str, path: str, body: dict | None = None, token: str = "", timeout: int = 180):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
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


def cleanup(session_id: int | None, user_id: int | None) -> None:
    if session_id:
        with session_factory() as db:
            db.query(interview_question).filter(
                interview_question.session_id == session_id
            ).delete()
            row = db.get(interview_session, session_id)
            if row:
                db.delete(row)
            db.commit()
    if user_id:
        for key in redis_client.scan_iter(f"interview:daily:{user_id}:*"):
            redis_client.delete(key)


def main() -> int:
    status, payload = call("POST", "/auth/login", {"phone": PHONE, "password": PASSWORD})
    if status != 200:
        print(f"学员登录失败：{status} {payload}")
        return 1
    token = payload["data"]["access_token"]
    user_id = int(payload["data"]["user"]["id"])

    status, payload = call("GET", "/interviews/quota", token=token)
    quota = (payload or {}).get("data", {})
    check(
        "配额接口返回上限/已用/剩余/重置时间",
        status == 200
        and quota.get("daily_limit") == settings_cache.interview_daily_limit
        and "remaining" in quota
        and (quota.get("reset_at") or "").endswith("Z"),
        str(quota),
    )
    # 账号可能当天已有消耗，按「本场新增 1 次」判断，不假设从 0 开始
    base_used = quota.get("used", 0)

    status, payload = call("GET", "/subjects?page=1&page_size=10", token=token)
    subjects = (payload or {}).get("data", {}).get("list", [])
    if not subjects:
        print("库里没有学科，先建一个再测")
        return 1
    subject_id = subjects[0]["id"]

    print(f"\n发起面试（学科 {subjects[0]['name']}），出题可能需要几十秒 …")
    status, payload = call("POST", "/interviews", {"source": 1, "subject_id": subject_id}, token)
    data = (payload or {}).get("data") or {}
    check("发起面试返回 201", status == 201, str(payload)[:300])
    check("生成 5 道题", data.get("question_count") == 5 and len(data.get("questions", [])) == 5, str(data)[:200])
    check(
        "题目带来源文档名、不含分数",
        all(item.get("source_doc_name") for item in data.get("questions", []))
        and all("score" not in item for item in data.get("questions", [])),
        str(data.get("questions", []))[:200],
    )
    session_id = int(data.get("id") or 0)
    if not session_id:
        cleanup(None, user_id)
        return 1
    print(f"  会话 {session_id}，首题：{data['questions'][0]['question_text'][:50]}")

    status, payload = call("GET", f"/interviews/{session_id}", token=token)
    detail = (payload or {}).get("data", {})
    check(
        "会话状态：进行中、剩余时间>0、当前题=1",
        status == 200
        and detail.get("status") == 1
        and detail.get("remaining_seconds", 0) > 0
        and detail.get("current_index") == 1,
        str(detail)[:200],
    )

    answer = (
        "这块我在项目里落地过：先用大模型做意图识别，把用户问题拆成可执行的步骤，"
        "再通过检索把业务知识注入上下文，最后用工作流把多步任务串起来，"
        "期间重点处理了上下文裁剪、工具调用失败重试和结果校验。"
    )
    print("\n作答第 1 题（调用模型评分）…")
    status, payload = call(
        "POST",
        f"/interviews/{session_id}/questions/1/answers",
        {"answer_mode": 2, "answer_text": answer},
        token,
    )
    first = (payload or {}).get("data") or {}
    check(
        "作答返回分数与点评",
        status == 200 and isinstance(first.get("score"), (int, float)) and first.get("ai_comment"),
        str(first)[:200],
    )
    print(f"  得分 {first.get('score')}，点评：{str(first.get('ai_comment'))[:60]}")

    print("\n触发追问 …")
    status, payload = call("POST", f"/interviews/{session_id}/questions/1/follow-ups", token=token)
    follow = (payload or {}).get("data") or {}
    check(
        "追问返回内容",
        status == 200 and follow.get("follow_up_text") and follow.get("follow_up_used") is True,
        str(follow)[:200],
    )
    print(f"  追问：{str(follow.get('follow_up_text'))[:60]}")

    status, payload = call("POST", f"/interviews/{session_id}/questions/1/follow-ups", token=token)
    check("同一题再次追问返回 409/50004", status == 409 and payload["code"] == 50004, str(payload))

    status, payload = call(
        "POST",
        f"/interviews/{session_id}/questions/1/answers",
        {"answer_mode": 2, "answer_text": "多进程可以绕开 GIL。", "is_follow_up": True},
        token,
    )
    check("回答追问成功且分数为两次平均", status == 200 and payload["data"].get("score") is not None, str(payload)[:200])

    status, payload = call("POST", f"/interviews/{session_id}/ws-tickets", token=token)
    check(
        "WS 票据 60 秒有效",
        status == 201 and payload["data"].get("expires_in") == 60 and payload["data"].get("ticket"),
        str(payload)[:160],
    )

    status, payload = call("PATCH", f"/interviews/{session_id}", {"status": 2}, token)
    finished = (payload or {}).get("data") or {}
    check(
        "结束面试返回总分与时长",
        status == 200 and finished.get("status") == 2 and isinstance(finished.get("total_score"), (int, float)),
        str(finished),
    )
    print(f"  总分 {finished.get('total_score')}，时长 {finished.get('duration_seconds')}s")

    status, payload = call(
        "POST",
        f"/interviews/{session_id}/questions/2/answers",
        {"answer_mode": 2, "answer_text": "已结束还在答题"},
        token,
    )
    check("结束后作答返回 409/50002", status == 409 and payload["code"] == 50002, str(payload))

    status, payload = call("GET", "/interviews?page=1&page_size=10", token=token)
    records = (payload or {}).get("data", {})
    check(
        "记录列表含本场且带总分",
        status == 200 and any(str(item["id"]) == str(session_id) for item in records.get("list", [])),
        str(records)[:200],
    )

    status, payload = call("GET", "/interviews/quota", token=token)
    check(
        "本场消耗 1 次配额",
        (payload or {}).get("data", {}).get("used") == base_used + 1,
        str(payload)[:160],
    )

    cleanup(session_id, user_id)
    print("-" * 40)
    print(f"通过 {PASSED} 项，失败 {FAILED} 项")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
