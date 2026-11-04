"""发送一条真实测试短信到指定号码（会消耗一次发码配额）。

仅用于联调：验证阿里云签名、模板、模板参数（${min}）是否正确。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\send_test_code.py 198xxxxxxxx
"""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python scripts/send_test_code.py <手机号>")
        return 1

    phone = sys.argv[1].strip()
    body = json.dumps({"phone": phone, "scene": "register"}).encode("utf-8")
    request = urllib.request.Request(BASE + "/auth/sms-codes", data=body, method="POST")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
            print(f"OK   已发送：{payload['data']}（请查看手机短信）")
            return 0
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode("utf-8") or "{}")
        print(f"FAIL HTTP {exc.code} code={payload.get('code')} message={payload.get('message')}")
        print("     模板参数/签名问题看这里；频繁触发看 20006")
        return 1


if __name__ == "__main__":
    sys.exit(main())
