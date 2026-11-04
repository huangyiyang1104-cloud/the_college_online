"""探测腾讯云 TTS 可用音色 ID。

超自然大模型音色与标准音色走不同资源包，ID 也不同；
先用几个常见的大模型音色 ID 试，成功即打印出可用值。
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.integrations import tencent_tts  # noqa: E402

# 超自然大模型音色（502 / 602 / 603 段），对应「超自然大模型语音合成 2 万字符」资源包
CANDIDATES = [
    502001,  # 智小柔 · 聊天女声
    502003,  # 智小敏 · 聊天女声
    502004,  # 智小满 · 营销女声
    502006,  # 智小悟 · 聊天男声
    602003,  # 爱小悠 · 聊天女声
    602005,  # 专业梓欣 · 聊天女声
    603001,  # 潇湘妹妹 · 特色女声
    603007,  # 邻家女孩 · 聊天女声
]

TEXT = "测试"


def main() -> int:
    ok_ids = []
    for voice_id in CANDIDATES:
        data = tencent_tts.synthesize(TEXT, timeout=15, voice_type=voice_id)
        if data:
            ok_ids.append(voice_id)
            print(f"OK   VoiceType={voice_id}  -> {len(data)} 字节")
        else:
            print(f"FAIL VoiceType={voice_id}")

    print("-" * 40)
    if ok_ids:
        print("可用音色 ID：", ", ".join(str(item) for item in ok_ids))
        print("把其中一个填进 backend/.env 的 TENCENT_TTS_VOICE_TYPE")
        return 0
    print("没有可用 ID。去控制台「语音合成 → 体验中心」试听，页面上会标注每个音色的 VoiceType")
    return 1


if __name__ == "__main__":
    sys.exit(main())
