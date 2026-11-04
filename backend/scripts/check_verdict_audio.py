"""验证面试结语语音：发起 → 直接结算（不答题=0 分=失败分支）→ 轮询音频。

跑完会清理会话与配额，可重复执行。
用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts/check_verdict_audio.py
"""

import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.cache import redis_client  # noqa: E402
from app.core.db import session_factory  # noqa: E402
from app.models import interview_question, interview_session  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
PHONE = "19880836572"
PASSWORD = "Abc123456"


def call(method: str, path: str, body: dict | None = None, token: str = "", raw: bool = False):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
            if raw:
                return response.status, payload
            return response.status, (json.loads(payload) if payload else None)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def main() -> int:
    status, payload = call("POST", "/auth/login", {"phone": PHONE, "password": PASSWORD})
    if status != 200:
        print(f"登录失败 {status}")
        return 1
    token = payload["data"]["access_token"]
    user_id = int(payload["data"]["user"]["id"])

    status, payload = call("GET", "/subjects?page=1&page_size=5", token=token)
    subjects = payload["data"]["list"]
    if not subjects:
        print("没有学科")
        return 1

    print(f"发起面试（{subjects[0]['name']}）…")
    status, payload = call("POST", "/interviews", {"source": 1, "subject_id": subjects[0]["id"]}, token)
    if status != 201:
        print(f"发起失败 {status} {payload}")
        return 1
    session_id = int(payload["data"]["id"])

    print("直接结束（未作答 → 0 分 → 失败分支）…")
    status, payload = call("PATCH", f"/interviews/{session_id}", {"status": 2}, token)
    if status != 200:
        print(f"结算失败 {status} {payload}")
        return 1
    result = payload["data"]
    print(f"  总分 {result['total_score']}，通过={result['passed']}，结论：{result['summary']}")
    print("  台词由后台生成，见后端日志中的『面试结语』记录")

    ok = False
    start = time.time()
    for attempt in range(1, 21):
        status, data = call("GET", f"/interviews/{session_id}/verdict-audio", token=token, raw=True)
        if status == 200 and isinstance(data, bytes) and data[:4] == b"RIFF":
            print(f"OK   结语音频就绪：{len(data)} 字节（等待 {time.time() - start:.1f}s）")
            ok = True
            break
        time.sleep(1.5)

    if not ok:
        print("FAIL 30 秒内未拿到结语音频（看后端日志里的『面试结语』记录）")

    with session_factory() as db:
        db.query(interview_question).filter(interview_question.session_id == session_id).delete()
        row = db.get(interview_session, session_id)
        if row:
            db.delete(row)
        db.commit()
    for key in redis_client.scan_iter(f"interview:daily:{user_id}:*"):
        redis_client.delete(key)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
