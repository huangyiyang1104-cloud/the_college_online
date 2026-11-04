# 启动 RVC 变声微服务（独立进程，端口 8010）
#
# 依赖装在 D:\rvc-venv（Python 3.11 + 复用 pill_train 的 GPU 版 torch），
# 不污染后端环境（后端是 3.14，装不了 fairseq / faiss）。
#
# 用法：powershell -ExecutionPolicy Bypass -File start.ps1

$ErrorActionPreference = 'Stop'

$venvPython = 'D:\rvc-venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
  Write-Error "找不到 $venvPython，先建环境并安装依赖（见 README 步骤）"
  exit 1
}

# ffmpeg 必须可被 infer_rvc_python 调用，否则读音频直接失败
$env:PATH = 'D:\rvc-venv\bin;' + $env:PATH

# 模型都放在纯英文路径：faiss 读不了中文路径
$env:RVC_MODEL_DIR = 'D:\rvc-venv\models\tomorin'
$env:RVC_HUBERT_DIR = 'D:\rvc-venv\models\hubert_base'
$env:RVC_RMVPE_PATH = 'D:\rvc-venv\models\rmvpe.pt'

$env:RVC_F0_METHOD = 'rmvpe'
# TTS 本身就是女声，转女声音色不需要变调；男声素材可设 12
$env:RVC_PITCH = '0'

Set-Location $PSScriptRoot
& $venvPython -m uvicorn app:app --host 127.0.0.1 --port 8010
