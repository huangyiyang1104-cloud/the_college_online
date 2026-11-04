"""腾讯云一句话识别（ASR）：WAV 字节 → 文本。

为什么不用 WebSocket 实时流式：
  面试作答本质是「说完一段独白」，说完再转写足够；
  而且转写结果要允许学员改错别字，边听边出字幕反而没有收益。
  流式需要双向转发 + 音频分片 + 断线重连，复杂度约为本方案三倍。

任何失败（密钥缺失、网络、额度、格式不对）都返回 None，由业务层提示重试，
不把异常抛给上层。
"""

import base64
import json
import logging

from tencentcloud.asr.v20190614 import asr_client, models
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile

from app.core.config import settings_cache

logger = logging.getLogger("yunshu.asr")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

DEFAULT_ENGINE = "16k_zh"
MAX_AUDIO_BYTES = 3 * 1024 * 1024  # 腾讯云单次上限约 60 秒，3MB 足够且留余量


def _client(timeout: int) -> asr_client.AsrClient:
    cred = credential.Credential(
        settings_cache.tencent_secret_id, settings_cache.tencent_secret_key
    )
    http_profile = HttpProfile()
    http_profile.endpoint = "asr.tencentcloudapi.com"
    http_profile.reqTimeout = timeout

    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile
    return asr_client.AsrClient(cred, "ap-guangzhou", client_profile)


def recognize(wav_bytes: bytes, timeout: int = 20) -> str | None:
    """识别一段 WAV（16k/单声道/16bit），返回文本；无法识别或失败返回 None。"""
    if not wav_bytes:
        return None
    if len(wav_bytes) > MAX_AUDIO_BYTES:
        logger.warning("音频超出上限：%s 字节", len(wav_bytes))
        return None
    if not settings_cache.tencent_secret_id or not settings_cache.tencent_secret_key:
        logger.warning("未配置腾讯云密钥，跳过语音识别")
        return None

    request = models.SentenceRecognitionRequest()
    request.from_json_string(
        json.dumps(
            {
                "EngSerViceType": settings_cache.tencent_asr_engine_model or DEFAULT_ENGINE,
                "SourceType": 1,  # 1 = 音频数据（base64）
                "VoiceFormat": "wav",
                "Data": base64.b64encode(wav_bytes).decode("ascii"),
                "DataLen": len(wav_bytes),
                "ProjectId": 0,
                "SubServiceType": 2,  # 2 = 一句话识别
            }
        )
    )

    try:
        response = _client(timeout).SentenceRecognition(request)
        payload = json.loads(response.to_json_string())
    except Exception as exc:
        logger.warning("语音识别失败：%s %s", type(exc).__name__, str(exc)[:200])
        return None

    text = (payload.get("Result") or "").strip()
    # 只记长度与耗时，不把学员作答内容写进日志
    logger.info("语音识别完成：%s 字节 → %s 字", len(wav_bytes), len(text))
    return text or None
