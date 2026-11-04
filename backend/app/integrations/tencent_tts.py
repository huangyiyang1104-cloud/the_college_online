"""腾讯云语音合成（TTS）：文本 → WAV 音频字节。

用官方 SDK 的 TextToVoice（一句话合成）。输出固定 16k / 单声道 / WAV，
正好是 RVC 推理与浏览器播放都能直接吃的格式。

任何失败都返回 None，由业务层降级为「只显示文字、不播报」。
"""

import base64
import json
import logging
import uuid

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.tts.v20190823 import models, tts_client

from app.core.config import settings_cache

logger = logging.getLogger("yunshu.tts")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

# 602005 = 专业梓欣（超自然大模型音色）。必须与资源包类型匹配：
# 502/602/603 段走「超自然大模型」包，501/601 段走「大模型音色」包
DEFAULT_VOICE_TYPE = 602005
SAMPLE_RATE = 16000


def _client(timeout: int) -> tts_client.TtsClient:
    cred = credential.Credential(
        settings_cache.tencent_secret_id, settings_cache.tencent_secret_key
    )
    http_profile = HttpProfile()
    http_profile.endpoint = "tts.tencentcloudapi.com"
    http_profile.reqTimeout = timeout

    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile
    return tts_client.TtsClient(cred, "ap-guangzhou", client_profile)


def synthesize(text: str, timeout: int = 30, voice_type: int | None = None) -> bytes | None:
    """合成一段语音，返回 WAV 字节；失败返回 None。

    voice_type 用于临时覆盖配置（探测可用音色时用），正式调用走配置。
    """
    text = (text or "").strip()
    if not text:
        return None
    if not settings_cache.tencent_secret_id or not settings_cache.tencent_secret_key:
        logger.warning("未配置腾讯云密钥，跳过语音合成")
        return None

    if voice_type:
        voice_id = int(voice_type)
    else:
        configured = settings_cache.tencent_tts_voice_type
        try:
            voice_id = int(configured) if str(configured).strip() else DEFAULT_VOICE_TYPE
        except (TypeError, ValueError):
            voice_id = DEFAULT_VOICE_TYPE

    request = models.TextToVoiceRequest()
    request.from_json_string(
        json.dumps(
            {
                "Text": text[:150],
                "SessionId": uuid.uuid4().hex,
                "VoiceType": voice_id,
                "Codec": "wav",
                "SampleRate": SAMPLE_RATE,
                "Speed": 0,
                "Volume": 0,
            }
        )
    )

    try:
        response = _client(timeout).TextToVoice(request)
        payload = json.loads(response.to_json_string())
        audio = payload.get("Audio")
    except Exception as exc:
        logger.warning("语音合成失败：%s %s", type(exc).__name__, str(exc)[:200])
        return None

    if not audio:
        logger.warning("语音合成返回空音频")
        return None

    try:
        return base64.b64decode(audio)
    except Exception:
        logger.warning("语音合成返回的 Audio 不是合法 base64")
        return None
