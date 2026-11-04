# 云枢智学 · 一键部署（Windows PowerShell）
#
# 用法：在 deploy 目录执行
#   powershell -ExecutionPolicy Bypass -File .\up.ps1
#   加 -SkipBuild 可跳过前端与镜像构建（只重启容器）
#
# 为什么不用 docker compose build：
#   本机 docker compose v5 + buildx 的 bake 机制会报 "failed to execute bake"，
#   而 docker build 正常，所以这里先构建镜像，再用 --no-build 起容器。
#
# RVC 微服务为什么不进容器：
#   它需要 NVIDIA GPU，容器内跑不了 CUDA；所以留在宿主机用独立 Python 3.11 跑，
#   容器通过 host.docker.internal:8010 访问（compose 里已配 extra_hosts）。

param([switch]$SkipBuild)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $PSScriptRoot

try {
    if (-not (Test-Path ".env")) {
        Write-Host "缺少 deploy/.env，先复制模板：copy .env.example .env" -ForegroundColor Yellow
        exit 1
    }
    if (-not (Test-Path "../backend/.env")) {
        Write-Host "缺少 backend/.env（应用配置），请先复制模板并填写" -ForegroundColor Yellow
        exit 1
    }
    # 管理端 Basic Auth 凭据由 .env 生成，避免密码散落在多个文件里
    Write-Host "`n[0/5] 生成管理端 Basic Auth 凭据 ..." -ForegroundColor Cyan
    $pythonExe = "$Root\backend\.venv\Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) { $pythonExe = "python" }
    & $pythonExe gen_htpasswd.py
    if ($LASTEXITCODE -ne 0) { throw "生成 .htpasswd 失败（检查 deploy/.env 的 NGINX_BASIC_AUTH_*）" }

    if (-not $SkipBuild) {
        Write-Host "`n[1/5] 构建学员端 ..." -ForegroundColor Cyan
        Push-Location "$Root\frontend-student"
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "学员端构建失败" }
        Pop-Location

        Write-Host "`n[2/5] 构建管理端 ..." -ForegroundColor Cyan
        Push-Location "$Root\frontend-admin"
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "管理端构建失败" }
        Pop-Location

        Write-Host "`n[3/5] 构建后端镜像 ..." -ForegroundColor Cyan
        docker build -t yunshu-api:local ../backend
        if ($LASTEXITCODE -ne 0) { throw "镜像构建失败" }
    } else {
        Write-Host "[1-3/5] 跳过构建" -ForegroundColor DarkGray
    }

    Write-Host "`n[4/5] 启动容器（基础设施 + 应用）..." -ForegroundColor Cyan
    docker compose --profile app up -d --no-build
    if ($LASTEXITCODE -ne 0) { throw "容器启动失败" }

    Write-Host "`n[5/6] 同步管理端账号密码（读 backend/.env 的 ADMIN_INIT_PASSWORD）..." -ForegroundColor Cyan
    Write-Host "  等数据库就绪 ..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 8
    & $pythonExe "$Root\backend\scripts\reset_admin_password.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  跳过：ADMIN_INIT_PASSWORD 未配置或密码不足 10 位" -ForegroundColor Yellow
    }

    Write-Host "`n[6/6] 启动 RVC 变声微服务（宿主机 GPU）..." -ForegroundColor Cyan
    $rvcPython = "D:\rvc-venv\Scripts\python.exe"
    if (Test-Path $rvcPython) {
        $rvcRunning = $false
        try {
            $null = Invoke-WebRequest -Uri "http://127.0.0.1:8010/health" -UseBasicParsing -TimeoutSec 3
            $rvcRunning = $true
        } catch {
            $rvcRunning = $false
        }

        if ($rvcRunning) {
            Write-Host "  RVC 已在运行，跳过" -ForegroundColor DarkGray
        } else {
            $env:PATH = "D:\rvc-venv\bin;" + $env:PATH
            $env:RVC_MODEL_DIR = "D:\rvc-venv\models\tomorin"
            $env:RVC_HUBERT_DIR = "D:\rvc-venv\models\hubert_base"
            $env:RVC_RMVPE_PATH = "D:\rvc-venv\models\rmvpe.pt"
            Set-Location "$Root\rvc-service"
            Start-Process -FilePath $rvcPython `
                -ArgumentList "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8010" `
                -WindowStyle Hidden `
                -RedirectStandardOutput "D:\rvc-venv\rvc.out.log" `
                -RedirectStandardError "D:\rvc-venv\rvc.err.log"
            Write-Host "  RVC 已后台启动，模型加载约 20 秒" -ForegroundColor DarkGray
        }
        Set-Location $PSScriptRoot
    } else {
        Write-Host "  未找到 $rvcPython，跳过 RVC（语音将只播 TTS 原声，不变声）" -ForegroundColor Yellow
    }

    Write-Host "`n等待服务就绪 ..." -ForegroundColor Cyan
    Start-Sleep -Seconds 12

    Write-Host "`n当前状态：" -ForegroundColor Cyan
    docker compose --profile app ps

    Write-Host "`n访问地址：" -ForegroundColor Green
    Write-Host "  学员端   http://localhost/"
    Write-Host "  管理端   http://localhost/admin/   （Basic Auth: admin / 见 deploy/.htpasswd）"
    Write-Host "  健康检查 http://localhost/api/v1/health"

    Write-Host "`n验证：" -ForegroundColor Green
    try {
        $health = Invoke-WebRequest -Uri "http://localhost/api/v1/health" -UseBasicParsing -TimeoutSec 10
        Write-Host "  /api/v1/health → $($health.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "  /api/v1/health 未就绪，看 docker logs yunshu-api --tail 40" -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}
