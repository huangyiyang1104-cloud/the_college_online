"""验证题目语音接口：发起面试 → 拉取音频 → 校验 WAV 头。

跑完会清理会话与当日配额，可重复执行。
用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts/smoke_audio.py
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.cache import redis_client  # noqa: E402
from app.core.db import session_factory  # noqa: E402
from app.models import interview_question, interview_session  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
PHONE = "19880836572"
PASSWORD = "Abc123456"


def call(method: str, path: str, body: dict | None = None, token: str = "", timeout: int = 180):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            if response.headers.get("Content-Type", "").startswith("audio/"):
                return response.status, raw
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def main() -> int:
    status, payload = call("POST", "/auth/login", {"phone": PHONE, "password": PASSWORD})
    if status != 200:
        print(f"登录失败 {status} {payload}")
        return 1
    token = payload["data"]["access_token"]
    user_id = int(payload["data"]["user"]["id"])

    status, payload = call("GET", "/subjects?page=1&page_size=5", token=token)
    subjects = payload["data"]["list"]
    if not subjects:
        print("没有学科，先建一个")
        return 1

    print(f"发起面试（{subjects[0]['name']}），出题 + 语音生成约需 60-90 秒 …")
    status, payload = call("POST", "/interviews", {"source": 1, "subject_id": subjects[0]["id"]}, token)
    if status != 201:
        print(f"发起失败 {status} {payload}")
        return 1
    session_id = int(payload["data"]["id"])
    print(f"会话 {session_id}，共 {payload['data']['question_count']} 题")

    ok = 0
    for index in range(1, payload["data"]["question_count"] + 1):
        status, data = call("GET", f"/interviews/{session_id}/questions/{index}/audio", token=token)
        if status == 200 and isinstance(data, bytes) and data[:4] == b"RIFF":
            print(f"  OK   第 {index} 题音频 {len(data)} 字节")
            ok += 1
        else:
            print(f"  FAIL 第 {index} 题：status={status}")

    print(f"\n语音就绪 {ok}/{payload['data']['question_count']} 题")

    with session_factory() as db:
        db.query(interview_question).filter(interview_question.session_id == session_id).delete()
        row = db.get(interview_session, session_id)
        if row:
            db.delete(row)
        db.commit()
    for key in redis_client.scan_iter(f"interview:daily:{user_id}:*"):
        redis_client.delete(key)

    return 0 if ok == payload["data"]["question_count"] else 1


if __name__ == "__main__":
    sys.exit(main())
