"""学员端认证与个人信息冒烟测试。

不真实发短信（会消耗额度并打扰手机），注册链路需要真机验证码，这里只覆盖：
白名单拦截、登录成败、个人信息读写、刷新轮换、跨端 token 隔离、退出。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\smoke_student.py
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.db import session_factory  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import user  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
TEST_PHONE = "13900000001"
TEST_PASSWORD = "abc123456"
PASSED = 0
FAILED = 0


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


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"OK   {label}")
    else:
        FAILED += 1
        print(f"FAIL {label} {detail}")


def setup_user() -> int:
    """准备一个已注册学员，返回 id。"""
    with session_factory() as db:
        existing = db.query(user).filter(user.phone == TEST_PHONE).one_or_none()
        if existing:
            existing.password_hash = hash_password(TEST_PASSWORD)
            existing.status = 1
            db.commit()
            return existing.id
        account = user(
            phone=TEST_PHONE,
            password_hash=hash_password(TEST_PASSWORD),
            nickname="冒烟学员",
            city="杭州",
            status=1,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        return account.id


def cleanup(user_id: int) -> None:
    with session_factory() as db:
        account = db.get(user, user_id)
        if account:
            db.delete(account)
            db.commit()


def main() -> int:
    status, payload = call("GET", "/health")
    check("健康检查", status == 200 and payload["code"] == 0, str(payload))

    status, payload = call("POST", "/auth/sms-codes", {"phone": "13700000000", "scene": "register"})
    check("非白名单号码发码被拒（20008）", status == 403 and payload["code"] == 20008, str(payload))

    user_id = setup_user()

    status, payload = call("POST", "/auth/login", {"phone": TEST_PHONE, "password": "wrongpass"})
    check("错误密码登录返回 20003", status == 401 and payload["code"] == 20003, str(payload))

    status, payload = call("POST", "/auth/login", {"phone": TEST_PHONE, "password": TEST_PASSWORD})
    check("登录成功并返回双 token", status == 200 and payload["data"].get("access_token"), str(payload))
    if status != 200:
        cleanup(user_id)
        return 1

    access = payload["data"]["access_token"]
    refresh_token = payload["data"]["refresh_token"]

    status, payload = call("GET", "/users/me", token=access)
    stats = (payload or {}).get("data", {}).get("stats", {})
    check(
        "个人信息含四项统计",
        status == 200 and set(stats) == {"course_completed", "paper_count", "wrong_count", "interview_count"},
        str(payload),
    )

    status, payload = call("PATCH", "/users/me", {"nickname": "改过的昵称", "city": "北京"}, access)
    check("修改昵称与城市", status == 200 and payload["data"]["nickname"] == "改过的昵称", str(payload))

    status, payload = call("GET", "/users/me")
    check("未带 token 访问返回 401", status == 401, str(payload))

    status, payload = call("POST", "/auth/tokens", {"refresh_token": refresh_token})
    check("刷新令牌成功", status == 200 and payload["data"].get("access_token"), str(payload))
    new_refresh = (payload or {}).get("data", {}).get("refresh_token", "")

    status, payload = call("POST", "/auth/tokens", {"refresh_token": refresh_token})
    check("旧 refresh 已失效（轮换）", status == 401 and payload["code"] == 20005, str(payload))

    status, payload = call("POST", "/auth/tokens", {"refresh_token": "bad.badtoken123456"})
    check("非法 refresh 返回 20005", status == 401 and payload["code"] == 20005, str(payload))

    status, payload = call("POST", "/admin/auth/login", {"username": "admin", "password": "admin123"})
    admin_access = (payload or {}).get("data", {}).get("access_token", "")
    status, payload = call("GET", "/users/me", token=admin_access)
    check("后台 token 不能访问学员接口", status == 401, str(payload))

    status, payload = call("POST", "/auth/logout", token=access)
    check("退出登录", status == 200 and payload["data"]["logged_out"] is True, str(payload))

    status, payload = call("POST", "/auth/register", {"phone": "13700000000", "code": "123456", "password": "abc123456"})
    check("非白名单号码注册被拒（20008）", status == 403 and payload["code"] == 20008, str(payload))

    status, payload = call(
        "POST", "/auth/register", {"phone": TEST_PHONE, "code": "123456", "password": "abcdef"}
    )
    check(
        "弱密码（纯字母）被参数校验拦截",
        status == 400 and payload["code"] == 10001,
        str(payload),
    )

    cleanup(user_id)
    print("-" * 40)
    print(f"通过 {PASSED} 项，失败 {FAILED} 项")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
