"""腾讯云 TTS 自检：合成一段中文并保存 WAV，验证密钥、音色与服务开通状态。

用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\check_tts.py [输出路径]
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.config import settings_cache  # noqa: E402
from app.integrations import tencent_tts  # noqa: E402

SAMPLE = "你好，我是云枢智学的面试官，接下来我们进行模拟面试，请听题。"


def main() -> int:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "tts_sample.wav")

    print(f"SecretId：{'已配置' if settings_cache.tencent_secret_id else '空'}")
    print(f"音色：{settings_cache.tencent_tts_voice_type or '默认 101001'}")

    data = tencent_tts.synthesize(SAMPLE)
    if not data:
        print("FAIL 合成失败，常见原因：密钥错误 / 语音合成未开通 / 免费包未领取 / 音色 ID 不存在")
        print("      详细原因看 backend 的 uvicorn.err.log（logger: yunshu.tts）")
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(f"OK   已保存 {out}（{len(data)} 字节，WAV 16k）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
