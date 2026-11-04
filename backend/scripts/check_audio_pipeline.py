"""验证面试语音链路：TTS → RVC 变声 → MinIO 入库。

不创建面试会话、不消耗面试配额，只走音频处理这一段。
用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\check_audio_pipeline.py
"""

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.config import settings_cache  # noqa: E402
from app.integrations import minio_storage, rvc  # noqa: E402
from app.services import audio_service  # noqa: E402

SAMPLE_SESSION = 999999
TEXT = "你好，我是云枢智学的面试官，我们开始第一道题。请先做个自我介绍。"


def main() -> int:
    print(f"TTS 音色      ：{settings_cache.tencent_tts_voice_type or '默认'}")
    print(f"RVC 开关      ：{settings_cache.rvc_enabled}")
    print(f"RVC 服务      ：{settings_cache.rvc_service_url}")

    health = rvc.healthy()
    print(f"RVC 健康检查  ：{health}")

    start = time.time()
    key = audio_service.generate(SAMPLE_SESSION, 1, TEXT)
    elapsed = time.time() - start

    if not key:
        print("FAIL 音频生成失败，看上面的告警日志")
        return 1

    data = minio_storage.download(key)
    print(f"OK   已入库：{key}（{len(data)} 字节，耗时 {elapsed:.1f}s）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
