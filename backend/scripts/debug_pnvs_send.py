"""直接调用阿里云发码接口并打印原始响应（排查参数问题用，不走 HTTP 接口）。

会真实下发一条短信。用法（在 backend 目录）：
    .venv\\Scripts\\python.exe scripts\\debug_pnvs_send.py
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from alibabacloud_dypnsapi20170525 import models as pnvs_models  # noqa: E402
from alibabacloud_tea_util import models as util_models  # noqa: E402

from app.core.config import settings_cache as s  # noqa: E402
from app.integrations.aliyun_pnvs import _client  # noqa: E402


def main() -> int:
    phone = s.test_phone_list[0]
    request = pnvs_models.SendSmsVerifyCodeRequest(
        phone_number=phone,
        sign_name=s.aliyun_pnvs_sign_name,
        template_code=s.aliyun_pnvs_template_code,
        # 模板变量 ${code} 需调用方自行提供（平台不会自动填充）
        template_param=json.dumps({"code": "123456", "min": str(s.aliyun_pnvs_valid_minutes)}),
        code_length=s.aliyun_pnvs_code_length,
        valid_time=s.aliyun_pnvs_valid_minutes * 60,
        interval=s.sms_resend_seconds,
    )
    print("请求参数：", request.to_map())

    try:
        response = _client().send_sms_verify_code_with_options(
            request, util_models.RuntimeOptions()
        )
    except Exception as exc:
        print(f"异常：{type(exc).__name__} code={getattr(exc, 'code', '')}")
        print(f"message={str(getattr(exc, 'message', exc))[:600]}")
        return 1

    print("返回：", json.dumps(response.body.to_map(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
