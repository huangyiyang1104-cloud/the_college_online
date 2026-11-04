"""RVC 变声微服务（独立进程 / 独立 Python 3.11 环境）。

后端通过 HTTP 调用：
    POST /convert   body 是 WAV 字节，响应也是 WAV 字节
    GET  /health    健康检查与模型信息

工程约束（都是踩过的坑）：
  - 模型必须放在纯英文路径：faiss 读不了中文路径（torch 自带的 FileIOReader 用 C 的 fopen）；
  - 音频转换必须给 ffmpeg 可用路径，否则 load_audio 直接 FileNotFoundError；
  - infer_rvc_python 的 __call__ 是「就地覆盖源文件」，所以在临时目录里操作，
    绝不碰调用方传进来的文件；
  - 模型常驻内存 + 串行锁：6GB 显存经不起并发推理，预热一次约 2.4 秒/段。
"""

import os
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

MODEL_DIR = Path(os.environ.get("RVC_MODEL_DIR", r"D:\rvc-venv\models\tomorin"))
PTH_PATH = Path(os.environ.get("RVC_PTH_PATH", str(MODEL_DIR / "tomorin.pth")))
INDEX_PATH = Path(os.environ.get("RVC_INDEX_PATH", str(MODEL_DIR / "tomorin.index")))

# 基础模型：所有音色共用，放在英文路径下
HUBERT_DIR = os.environ.get("RVC_HUBERT_DIR", r"D:\rvc-venv\models\hubert_base")
RMVPE_PATH = os.environ.get("RVC_RMVPE_PATH", r"D:\rvc-venv\models\rmvpe.pt")

TAG = "default"
F0_METHOD = os.environ.get("RVC_F0_METHOD", "rmvpe")
PITCH = int(os.environ.get("RVC_PITCH", "0"))
INDEX_RATE = float(os.environ.get("RVC_INDEX_RATE", "0.75"))
PROTECT = float(os.environ.get("RVC_PROTECT", "0.33"))
ONLY_CPU = os.environ.get("RVC_ONLY_CPU", "0") == "1"

_lock = threading.Lock()
_converter = None


def _converter_instance():
    """首次调用时加载并配置模型，之后复用（预热后单段约 2.4 秒）。"""
    global _converter
    if _converter is None:
        if not PTH_PATH.exists():
            raise HTTPException(500, f"音色模型不存在：{PTH_PATH}")
        if not Path(HUBERT_DIR).exists():
            raise HTTPException(500, f"hubert 基础模型不存在：{HUBERT_DIR}")

        from infer_rvc_python import BaseLoader

        loader = BaseLoader(
            only_cpu=ONLY_CPU, hubert_path=HUBERT_DIR, rmvpe_path=RMVPE_PATH
        )
        loader.apply_conf(
            tag=TAG,
            file_model=str(PTH_PATH),
            pitch_algo=F0_METHOD,
            pitch_lvl=PITCH,
            file_index=str(INDEX_PATH) if INDEX_PATH.exists() else "",
            index_influence=INDEX_RATE,
            consonant_breath_protection=PROTECT,
        )
        _converter = loader
    return _converter


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 启动即加载，避免首个请求等 20 秒
    try:
        _converter_instance()
    except Exception as exc:  # 模型缺失不阻止服务启动，/health 会暴露问题
        print(f"[warn] 模型预加载失败：{type(exc).__name__}: {exc}")
    yield


app = FastAPI(title="Yunshu RVC Service", version="0.2.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {
        "ok": _converter is not None,
        "model": PTH_PATH.name,
        "index": INDEX_PATH.name if INDEX_PATH.exists() else "",
        "hubert": Path(HUBERT_DIR).name,
        "rmvpe": Path(RMVPE_PATH).name,
        "device": "cpu" if ONLY_CPU else "cuda",
        "f0_method": F0_METHOD,
        "pitch": PITCH,
    }


@app.post("/convert")
async def convert(request: Request):
    data = await request.body()
    if not data:
        raise HTTPException(400, "请求体为空")

    converter = _converter_instance()

    with _lock:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "in.wav"
            source.write_bytes(data)

            try:
                converter(
                    audio_files=[str(source)],
                    tag_list=[TAG],
                    overwrite=True,
                    type_output="wav",
                    show_progress=False,
                )
            except Exception as exc:
                raise HTTPException(
                    500, f"RVC 推理失败：{type(exc).__name__}: {exc}"
                ) from exc

            outputs = getattr(converter, "output_list", None) or []
            if not outputs:
                raise HTTPException(500, "RVC 未产出音频")

            result = Path(outputs[0])
            if not result.exists():
                raise HTTPException(500, "RVC 输出文件不存在")

            return Response(content=result.read_bytes(), media_type="audio/wav")
