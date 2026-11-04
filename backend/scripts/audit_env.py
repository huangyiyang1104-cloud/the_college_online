"""环境变量审计：比对 .env 的实际键与代码中定义的配置项。

检查三件事：
  1. 代码里有定义、.env 里却没写的键（可能靠默认值跑，容易在部署时踩坑）
  2. .env 里写了、但代码根本没定义的键（配了不生效）
  3. 必填但当前为空的键

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\audit_env.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.config import BASE_DIR, settings_cache  # noqa: E402

# 允许为空的外部凭证（未到对应模块，不阻塞）
OPTIONAL_EMPTY = {
    "MINERU_API_URL",
    "MINERU_API_KEY",
    "TENCENT_TTS_VOICE_TYPE",
    "OSS_ENDPOINT",
    "OSS_BUCKET",
    # 号码认证：短信验证码场景走默认方案，不需要方案名；一键登录才填
    "ALIYUN_PNVS_SCHEME_NAME",
}


def read_env_keys(path: pathlib.Path) -> set[str]:
    if not path.exists():
        return set()
    keys: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        keys.add(line.split("=", 1)[0].strip())
    return keys


def main() -> int:
    env_keys = read_env_keys(BASE_DIR / ".env")
    example_keys = read_env_keys(BASE_DIR / ".env.example")

    fields = type(settings_cache).model_fields
    defined = {name.upper(): name for name in fields}

    missing_in_env = sorted(k for k in defined if k not in env_keys)
    extra_in_env = sorted(k for k in env_keys if k not in defined)
    empty_values = sorted(
        key
        for key, name in defined.items()
        if str(getattr(settings_cache, name, "")).strip() == ""
    )
    missing_in_example = sorted(k for k in defined if k not in example_keys)

    print(f"代码定义的配置项：{len(defined)} 个")
    print(f".env 中的键：{len(env_keys)} 个\n")

    print("== 1. .env 缺少的键（当前靠默认值）==")
    print("  无" if not missing_in_env else "\n".join(f"  - {k}" for k in missing_in_env))

    print("\n== 2. .env 多余、代码未定义的键（配了不生效）==")
    print("  无" if not extra_in_env else "\n".join(f"  - {k}" for k in extra_in_env))

    print("\n== 3. 为空的值 ==")
    if not empty_values:
        print("  无")
    else:
        for key in empty_values:
            tag = "（可空，未到对应模块）" if key in OPTIONAL_EMPTY else "（应为必填）"
            print(f"  - {key} {tag}")

    print("\n== 4. .env.example 缺少的键（模板不完整）==")
    print("  无" if not missing_in_example else "\n".join(f"  - {k}" for k in missing_in_example))

    blocking = [k for k in empty_values if k not in OPTIONAL_EMPTY]
    print(f"\n汇总：缺键 {len(missing_in_env)}，多余 {len(extra_in_env)}，"
          f"空值 {len(empty_values)}（其中必填 {len(blocking)}），模板缺 {len(missing_in_example)}")
    return 0 if not blocking else 1


if __name__ == "__main__":
    sys.exit(main())
