"""配置自检：确认 .env 被正确加载，并列出还没填的 API KEY。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\check_config.py
"""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.config import settings_cache as s  # noqa: E402

EXPECTED = [
    ("JWT_SECRET 长度", len(s.jwt_secret), 32),
    ("MySQL", f"{s.mysql_host}:{s.mysql_port}", "127.0.0.1:3307"),
    ("Redis", f"{s.redis_host}:{s.redis_port}", "127.0.0.1:6379"),
    ("MinIO", s.minio_endpoint, "127.0.0.1:9000"),
    ("Milvus", f"{s.milvus_host}:{s.milvus_port}", "127.0.0.1:19530"),
    ("LLM 模型", s.deepseek_model, "deepseek-4.1-flash"),
    ("Embedding 模型", s.embedding_model, "qwen3.7-text-embedding"),
    ("Embedding 维度", s.embedding_dim, 1024),
]

API_KEYS = [
    ("DEEPSEEK_API_KEY", s.deepseek_api_key),
    ("DASHSCOPE_API_KEY", s.dashscope_api_key),
    ("ALIYUN_ACCESS_KEY_ID", s.aliyun_access_key_id),
    ("ALIYUN_ACCESS_KEY_SECRET", s.aliyun_access_key_secret),
    ("OSS_ENDPOINT", s.oss_endpoint),
    ("OSS_BUCKET", s.oss_bucket),
    ("ALIYUN_PNVS_SIGN_NAME", s.aliyun_pnvs_sign_name),
    ("ALIYUN_PNVS_TEMPLATE_CODE", s.aliyun_pnvs_template_code),
    ("AUTH_TEST_PHONES（测试白名单）", ",".join(s.test_phone_list)),
    ("TENCENT_SECRET_ID", s.tencent_secret_id),
    ("TENCENT_SECRET_KEY", s.tencent_secret_key),
    ("TENCENT_APP_ID", s.tencent_app_id),
    ("MINERU_API_KEY", s.mineru_api_key),
]


def main() -> int:
    print("== 基础配置 ==")
    mismatch = 0
    for name, actual, expect in EXPECTED:
        ok = str(actual) == str(expect)
        mismatch += 0 if ok else 1
        print(f"{'OK  ' if ok else 'DIFF'} {name}: {actual}" + ("" if ok else f"（预期 {expect}）"))

    # 常见误填：bucket 写成带地域的完整域名
    if "." in s.oss_bucket:
        print("WARN OSS_BUCKET 疑似填成了域名，应只填 bucket 名（如 yunshu-school-online）")

    print("\n== 第三方凭证 ==")
    pending = 0
    for name, value in API_KEYS:
        filled = bool(str(value).strip())
        if name in os.environ:
            # 系统环境变量优先级高于 .env，此时 .env 里写什么都不生效
            source = "系统环境变量（覆盖 .env）"
        elif filled:
            source = ".env"
        else:
            source = "未配置"
            pending += 1
        print(f"{'已填' if filled else '空  '} {name:<26} 来源: {source}")

    print(f"\n汇总：基础配置异常 {mismatch} 项，待填凭证 {pending} 项")
    return 0 if mismatch == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
