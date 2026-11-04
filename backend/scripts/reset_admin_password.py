"""按 backend/.env 的 ADMIN_INIT_PASSWORD 重置管理端超管密码。

为什么做成脚本而不是启动时自动改：
  启动即改库会让"改密码"变成隐式副作用，排查问题时很迷惑；
  显式跑一次脚本，行为可预期，也方便在部署流程里单独一步执行。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts/reset_admin_password.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.config import settings_cache  # noqa: E402
from app.core.db import session_factory  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import admin_user  # noqa: E402

MIN_LENGTH = 10


def main() -> int:
    username = (settings_cache.admin_username or "").strip()
    password = settings_cache.admin_init_password or ""

    if not username:
        print("FAIL .env 里 ADMIN_USERNAME 为空")
        return 1
    if not password:
        print("FAIL .env 里 ADMIN_INIT_PASSWORD 为空，跳过（不把超管密码设成空串）")
        return 1
    if len(password) < MIN_LENGTH:
        print(f"FAIL 密码太短（至少 {MIN_LENGTH} 位），拒绝设置")
        return 1

    with session_factory() as db:
        row = db.execute(
            select(admin_user).where(admin_user.username == username)
        ).scalar_one_or_none()

        if row:
            row.password_hash = hash_password(password)
            row.status = 1
            action = "已重置"
        else:
            db.add(
                admin_user(
                    username=username,
                    password_hash=hash_password(password),
                    role=1,
                    status=1,
                    is_builtin=1,
                )
            )
            action = "已创建"

        db.commit()

    # 只回显账号与长度，不打印明文密码（避免进日志）
    print(f"OK {action}管理端账号「{username}」，密码长度 {len(password)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
