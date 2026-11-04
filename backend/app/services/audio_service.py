"""面试语音生成：TTS → （RVC 变声）→ MinIO。

两类音频：
  - 题目语音：发起面试时按题生成，播放时零等待；
  - 结语语音：面试结算后按结果生成（失败=让等通知，通过=问入职/薪资）。

生成失败一律返回 None，业务层降级为纯文字，不影响主流程。
"""

import logging

from app.core.config import settings_cache
from app.integrations import llm, minio_storage, rvc, tencent_tts

logger = logging.getLogger("yunshu.audio")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

AUDIO_PREFIX = "interview-audio"


def audio_key(session_id: int, question_index: int) -> str:
    """题目语音路径可推导，因此不需要在表里加字段。"""
    return f"{AUDIO_PREFIX}/{session_id}/{question_index}.wav"


def verdict_key(session_id: int) -> str:
    """结语语音，与题目音频按文件名区分。"""
    return f"{AUDIO_PREFIX}/{session_id}/verdict.wav"


def _synthesize_and_store(key: str, text: str) -> str | None:
    """TTS 合成 → RVC 变声（失败则用原声）→ 存入 MinIO。"""
    wav = tencent_tts.synthesize(text)
    if not wav:
        logger.warning("TTS 未产出音频 key=%s", key)
        return None

    converted = rvc.convert(wav)
    if converted:
        wav = converted

    try:
        return minio_storage.upload_at(key, wav, "audio/wav")
    except Exception:
        logger.warning("语音入库失败 key=%s", key)
        return None


def generate(session_id: int, question_index: int, text: str) -> str | None:
    """生成单题语音并入库，返回 object key。"""
    if not settings_cache.interview_audio_enabled:
        return None
    return _synthesize_and_store(audio_key(session_id, question_index), text)


def generate_many(session_id: int, items: list[tuple[int, str]]) -> int:
    """批量生成题目语音（串行，避免同时打爆 GPU / 触发 TTS 限频）。"""
    if not settings_cache.interview_audio_enabled:
        return 0

    done = 0
    for index, text in items:
        if generate(session_id, index, text):
            done += 1
    logger.info("语音预生成完成 session=%s 成功 %s/%s", session_id, done, len(items))
    return done


def generate_verdict(session_id: int, passed: bool, score: float) -> str | None:
    """生成面试结语语音：模型出台词 → TTS → RVC → MinIO。"""
    if not settings_cache.interview_audio_enabled:
        return None

    line = llm.generate_verdict_line(passed, score)
    if not line:
        return None

    logger.info("面试结语 session=%s passed=%s 台词：%s", session_id, passed, line)
    return _synthesize_and_store(verdict_key(session_id), line)


def load(session_id: int, question_index: int) -> bytes | None:
    """按约定路径读回题目音频；不存在返回 None。"""
    return _read(audio_key(session_id, question_index))


def load_verdict(session_id: int) -> bytes | None:
    """读回结语音频；不存在返回 None。"""
    return _read(verdict_key(session_id))


def _read(key: str) -> bytes | None:
    try:
        if not minio_storage.exists(key):
            return None
        return minio_storage.download(key)
    except Exception:
        return None
