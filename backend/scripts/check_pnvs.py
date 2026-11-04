"""号码认证配置自检（不发短信、不消耗额度）。

验证码由服务端生成并通过 ${code} 传给阿里云模板，校验在本地 Redis 完成，
因此这里只检查配置是否齐全，真实下发用 send_test_code.py 验证。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\check_pnvs.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.config import settings_cache as s  # noqa: E402

REQUIRED = [
    ("ALIYUN_ACCESS_KEY_ID", s.aliyun_access_key_id),
    ("ALIYUN_ACCESS_KEY_SECRET", s.aliyun_access_key_secret),
    ("ALIYUN_PNVS_ENDPOINT", s.aliyun_pnvs_endpoint),
    ("ALIYUN_PNVS_SIGN_NAME", s.aliyun_pnvs_sign_name),
    ("ALIYUN_PNVS_TEMPLATE_CODE", s.aliyun_pnvs_template_code),
    ("AUTH_TEST_PHONES", s.auth_test_phones),
]


def main() -> int:
    missing = [name for name, value in REQUIRED if not str(value).strip()]

    for name, value in REQUIRED:
        shown = "-" if not str(value).strip() else str(value)
        if name == "ALIYUN_ACCESS_KEY_SECRET":
            shown = f"{shown[:4]}****" if shown != "-" else shown
        print(f"{'OK  ' if str(value).strip() else 'MISS'} {name} = {shown}")

    phones = s.test_phone_list
    print(f"\n测试号码：{len(phones)} 个")
    for phone in phones:
        print(f"  {phone[:3]}****{phone[-4:]}")

    print(f"验证码：{s.aliyun_pnvs_code_length} 位，{s.aliyun_pnvs_valid_minutes} 分钟有效")
    print(f"发送间隔：{s.sms_resend_seconds} 秒，单日上限 {s.sms_daily_limit} 条")

    if missing:
        print(f"\nFAIL 缺少配置：{', '.join(missing)}")
        return 1

    print("\nOK   配置齐全。真实下发用：python scripts/send_test_code.py <手机号>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
