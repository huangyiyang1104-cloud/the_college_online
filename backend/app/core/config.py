"""应用配置：统一从环境变量 / .env 读取，避免散落在代码里。"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3307
    mysql_user: str = "yunshu"
    mysql_password: str = "yunshu_change_me"
    mysql_database: str = "yunshu"

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    minio_endpoint: str = "127.0.0.1:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minio_change_me"
    minio_bucket: str = "yunshu"
    minio_secure: bool = False

    # ---- 对象存储后端与上传限制 ----
    # minio：本地开发（文件进 MinIO）；oss：线上（文件进阿里云 OSS）
    storage_backend: str = "minio"
    upload_max_mb: int = 10

    jwt_secret: str = "dev_only_change_me_32_bytes_hex"
    access_token_minutes: int = 30
    refresh_token_days: int = 7

    # ---- 管理端初始账号（只给重置脚本用，不在运行时自动改库）----
    admin_username: str = "admin"
    admin_init_password: str = ""

    # ---- 向量库 ----
    milvus_host: str = "127.0.0.1"
    milvus_port: int = 19530
    milvus_collection_docs: str = "interview_doc_snippets"
    milvus_collection_resume: str = "resume_snippets"

    # ---- 业务参数（与 04 接口文档取值一致，集中调整）----
    interview_daily_limit: int = 3
    interview_minutes: int = 15
    # 面试通过线（百分制），结束结算时给出是否通过
    interview_pass_score: int = 60
    sms_resend_seconds: int = 60
    sms_daily_limit: int = 10
    log_level: str = "INFO"

    # ---- 大模型（DeepSeek，OpenAI 兼容）----
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-flash"

    # ---- Embedding（qwen，DashScope 兼容模式）----
    dashscope_api_key: str = ""
    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = "qwen3.7-text-embedding"
    embedding_dim: int = 1024

    # ---- 阿里云 AccessKey（OSS 与短信共用）----
    aliyun_access_key_id: str = ""
    aliyun_access_key_secret: str = ""

    # ---- 阿里云 OSS ----
    oss_endpoint: str = ""
    oss_bucket: str = ""

    # ---- 阿里云号码认证服务：注册验证码（测试手机号码，真实下发不计费）----
    aliyun_pnvs_endpoint: str = "dypnsapi.aliyuncs.com"
    aliyun_pnvs_sign_name: str = ""
    aliyun_pnvs_template_code: str = ""
    aliyun_pnvs_scheme_name: str = ""
    aliyun_pnvs_code_length: int = 6
    aliyun_pnvs_valid_minutes: int = 5
    # 测试号码白名单，逗号分隔；未在名单内的号码不发起阿里云调用
    auth_test_phones: str = ""

    # ---- 腾讯云语音：实时识别（ASR）+ 语音合成（TTS）----
    tencent_secret_id: str = ""
    tencent_secret_key: str = ""
    tencent_app_id: str = ""
    tencent_asr_engine_model: str = "16k_zh"
    tencent_asr_ws_url: str = "wss://asr.cloud.tencent.com/asr/v2"
    tencent_tts_voice_type: str = ""
    tencent_tts_codec: str = "mp3"

    # ---- RVC 变声（独立 Python 3.11 微服务，不进入后端进程）----
    rvc_enabled: bool = False
    rvc_service_url: str = "http://127.0.0.1:8010"
    rvc_timeout_seconds: int = 60
    # 变调：男声转女声通常 +12，女声转女声 0
    rvc_pitch: int = 0
    rvc_index_rate: float = 0.75
    rvc_protect: float = 0.33

    # ---- 面试语音预生成 ----
    interview_audio_enabled: bool = True

    # ---- MinerU（PDF → Markdown）----
    mineru_api_url: str = ""
    mineru_api_key: str = ""

    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def test_phone_list(self) -> list[str]:
        """测试号码白名单：只有名单内手机号可获取验证码。"""
        return [item.strip() for item in self.auth_test_phones.split(",") if item.strip()]


settings_cache = settings()
