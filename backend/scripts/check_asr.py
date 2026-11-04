"""ASR 自检：用 TTS 合成一段已知中文，再送识别，比对回读结果。

不依赖真实录音，可反复执行（每次消耗约 20 字 TTS 额度 + 1 次识别）。
用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\check_asr.py            # 只测识别
    .venv\\Scripts\\python.exe scripts/check_asr.py --http      # 另外走一遍 HTTP 接口
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.integrations import tencent_asr, tencent_tts  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
PHONE = "19880836572"
PASSWORD = "Abc123456"

SAMPLE = "我在项目里用 FastAPI 做过接口开发，主要负责题库模块和用户登录。"


def similarity(source: str, target: str) -> float:
    """极简相似度：公共字符占比（中文不需要分词即可粗判）。"""
    if not source or not target:
        return 0.0
    common = set(source) & set(target)
    return len(common) / max(len(set(source)), 1)


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
    print(f"原文：{SAMPLE}")

    wav = tencent_tts.synthesize(SAMPLE)
    if not wav:
        print("FAIL TTS 没产出音频，先确认 TTS 配置")
        return 1
    print(f"TTS：{len(wav)} 字节")

    text = tencent_asr.recognize(wav)
    if not text:
        print("FAIL 识别失败，常见原因：")
        print("      1) 子账号缺 QcloudASRFullAccess（报 UnauthorizedOperation，最常见）")
        print("      2) 实时/一句话识别服务未开通")
        print("      3) 免费额度已用完")
        return 1

    ratio = similarity(SAMPLE, text)
    print(f"识别：{text}")
    print(f"相似度：{ratio:.0%}")
    if ratio < 0.6:
        print("WARN 相似度偏低，可能是测试音频被 RVC 变声后失真，或采样率不匹配")
    else:
        print("OK 识别链路正常")

    if "--http" not in sys.argv:
        return 0

    status, payload = call("POST", "/auth/login", {"phone": PHONE, "password": PASSWORD})
    if status != 200:
        print(f"FAIL 登录失败 {status}")
        return 1
    token = payload["data"]["access_token"]

    status, payload = call("GET", "/subjects?page=1&page_size=5", token=token)
    subjects = payload["data"]["list"]
    if not subjects:
        print("FAIL 没有学科")
        return 1

    status, payload = call("POST", "/interviews", {"source": 1, "subject_id": subjects[0]["id"]}, token)
    if status != 201:
        print(f"FAIL 发起面试失败 {status}")
        return 1
    session_id = int(payload["data"]["id"])

    request = urllib.request.Request(f"{BASE}/interviews/{session_id}/asr", data=wav, method="POST")
    request.add_header("Content-Type", "audio/wav")
    request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        print(f"HTTP 接口：code={body.get('code')} text={body.get('data', {}).get('text')}")
    except urllib.error.HTTPError as exc:
        print(f"FAIL HTTP 接口返回 {exc.code}：{exc.read().decode('utf-8', 'ignore')[:200]}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
