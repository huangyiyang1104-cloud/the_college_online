"""用最近一次下发的验证码完成注册（联调用）。

验证码由服务端生成并存 Redis，这里直接读取，因此不需要手抄短信。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\register_test.py 198xxxxxxxx [密码]
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.cache import redis_client  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python scripts/register_test.py <手机号> [密码]")
        return 1

    phone = sys.argv[1].strip()
    password = sys.argv[2] if len(sys.argv) > 2 else "Abc123456"

    code = redis_client.get(f"sms:code:{phone}")
    if not code:
        print("FAIL 没有可用验证码（已过期或未发送），先跑 send_test_code.py")
        return 1
    print(f"读取到验证码：{code}（未消费）")

    body = json.dumps({"phone": phone, "code": code, "password": password}).encode("utf-8")
    request = urllib.request.Request(BASE + "/auth/register", data=body, method="POST")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"FAIL HTTP {exc.code} {exc.read().decode('utf-8')}")
        return 1

    user = payload["data"]["user"]
    print(f"OK   注册成功：{user['phone']}（昵称：{user['nickname'] or '空'}）")
    print(f"     密码：{password}")
    print(f"     access_token 前 24 位：{payload['data']['access_token'][:24]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
