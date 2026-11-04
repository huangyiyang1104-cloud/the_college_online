"""阿里云号码认证服务（dypnsapi）：发送与校验短信验证码。

通道为「测试手机号码」：短信真实下发到白名单号码、不产生费用。
验证码由阿里云生成并写入模板 ${code}，后端拿不到明文，因此校验只能交给
CheckSmsVerifyCode，不存在本地比对。
"""

import json
import logging
import secrets

from alibabacloud_dypnsapi20170525 import models as pnvs_models
from alibabacloud_dypnsapi20170525.client import Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

from app.core.config import settings_cache
from app.core.errors import api_error

logger = logging.getLogger("yunshu.pnvs")
# uvicorn 会接管 root logger，这里给本模块单独挂 handler，保证告警能落进日志文件
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

# 阿里云侧的发送频率限制（body.Code 或异常 code 都可能出现）
FREQUENCY_CODES = {"biz.FREQUENCY", "isv.BUSINESS_LIMIT_CONTROL"}


def _client() -> Client:
    config = open_api_models.Config(
        access_key_id=settings_cache.aliyun_access_key_id,
        access_key_secret=settings_cache.aliyun_access_key_secret,
    )
    config.endpoint = settings_cache.aliyun_pnvs_endpoint
    return Client(config)


def send_verify_code(phone: str) -> str:
    """发送验证码，返回本次生成的明文验证码（由调用方写入 Redis 后校验）。

    注意：模板里的 ${code} 需要【调用方提供】，阿里云不会自动填充；
    因此验证码由我们生成，校验也在服务端本地完成（见 cache.verify_sms_code）。
    """
    verify_code = f"{secrets.randbelow(1_000_000):06d}"
    request = pnvs_models.SendSmsVerifyCodeRequest(
        phone_number=phone,
        sign_name=settings_cache.aliyun_pnvs_sign_name,
        template_code=settings_cache.aliyun_pnvs_template_code,
        # TemplateParam 必须是 JSON 字符串，传 dict 会被 SDK 当成未传（MissingTemplateParam）
        template_param=json.dumps(
            {
                "code": verify_code,
                "min": str(settings_cache.aliyun_pnvs_valid_minutes),
            }
        ),
        code_length=settings_cache.aliyun_pnvs_code_length,
        # 注意：valid_time 单位是【秒】，配置里存的是分钟
        valid_time=settings_cache.aliyun_pnvs_valid_minutes * 60,
        interval=settings_cache.sms_resend_seconds,
        scheme_name=settings_cache.aliyun_pnvs_scheme_name or None,
    )

    try:
        response = _client().send_sms_verify_code_with_options(
            request, util_models.RuntimeOptions()
        )
    except Exception:
        logger.exception("阿里云发码调用异常 phone=%s", phone)
        raise api_error(10008, "验证码服务暂不可用，请稍后重试", 503)

    body = response.body
    if not body or body.code != "OK":
        code = getattr(body, "code", None)
        logger.warning(
            "阿里云发码返回失败 phone=%s code=%s message=%s",
            phone,
            code,
            getattr(body, "message", None),
        )
        if code in FREQUENCY_CODES:
            # 阿里云侧限频（同号短时间多次请求），与本地 60 秒冷却不同，需要更久
            raise api_error(20006, "验证码发送过于频繁，请稍后再试", 429)
        raise api_error(10008, "验证码发送失败，请稍后重试", 503)

    return verify_code
