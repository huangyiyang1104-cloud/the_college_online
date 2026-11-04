"""按 deploy/.env 的 NGINX_BASIC_AUTH_* 生成管理端 Basic Auth 的 .htpasswd。

为什么单独一个脚本：
  密码写在 .env 里，凭据文件由脚本生成，避免密码在多个文件里各存一份。
  改完密码重跑本脚本 + 重启 nginx 即可生效。

依赖 openssl（Windows 上 Git 自带的或 MinGW 的都行）：
  nginx 只认 crypt / apr1 格式，Python 标准库不提供这两种加密，所以借 openssl。

用法（在 deploy 目录）：
    python gen_htpasswd.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

ENV_FILE = Path(__file__).with_name(".env")
TARGET = Path(__file__).with_name(".htpasswd")

OPENSSL_CANDIDATES = (
    r"D:\C\mingw64\bin\openssl.exe",
    r"C:\Program Files\Git\usr\bin\openssl.exe",
    r"C:\Program Files (x86)\Git\usr\bin\openssl.exe",
)


def find_openssl() -> str | None:
    found = shutil.which("openssl")
    if found:
        return found
    for candidate in OPENSSL_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


def read_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def main() -> int:
    env = read_env(ENV_FILE)
    user = env.get("NGINX_BASIC_AUTH_USER", "").strip()
    password = env.get("NGINX_BASIC_AUTH_PASSWORD", "").strip()

    if not user or not password:
        print("FAIL deploy/.env 里 NGINX_BASIC_AUTH_USER 或 NGINX_BASIC_AUTH_PASSWORD 为空")
        return 1

    openssl = find_openssl()
    if not openssl:
        print("FAIL 找不到 openssl，请安装 Git for Windows 或把 openssl 加进 PATH")
        return 1

    result = subprocess.run(
        [openssl, "passwd", "-apr1", password],
        capture_output=True,
        text=True,
    )
    digest = (result.stdout or "").strip()
    if result.returncode != 0 or not digest:
        print(f"FAIL openssl 生成失败：{result.stderr.strip()[:200]}")
        return 1

    TARGET.write_text(f"{user}:{digest}", encoding="ascii")
    print(f"OK 已生成 {TARGET.name}（用户 {user}，密码长度 {len(password)}）")
    print("   生效：docker compose restart nginx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
