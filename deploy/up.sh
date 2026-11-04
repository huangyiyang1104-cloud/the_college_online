#!/usr/bin/env bash
# 云枢智学 · 一键部署（Linux / macOS）
#
# 用法：
#   cd deploy && chmod +x up.sh && ./up.sh
#
# 与 up.ps1 等价：先 docker build 再 --no-build 起容器，
# 绕过部分环境下 docker compose build 的 bake 报错。

set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
    echo "缺少 deploy/.env，先执行：cp .env.example .env" >&2
    exit 1
fi
if [ ! -f "../backend/.env" ]; then
    echo "缺少 backend/.env（应用配置），请先复制模板并填写" >&2
    exit 1
fi

echo
echo "[1/3] 构建后端镜像 ..."
docker build -t yunshu-api:local ../backend

echo
echo "[2/3] 启动全部服务（基础设施 + 应用）..."
docker compose --profile app up -d --no-build

echo
echo "[3/3] 当前状态："
docker compose --profile app ps

echo
echo "访问地址："
echo "  学员端   http://localhost/"
echo "  管理端   http://localhost/admin/"
echo "  接口文档 http://localhost/api/docs"
