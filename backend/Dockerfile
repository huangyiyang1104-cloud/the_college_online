# 云枢智学 · API / Worker 镜像
#
# 构建：docker compose --profile app build
# 说明：
#   - 依赖只从 requirements.txt 安装，本地 venv 装的包不会进镜像
#   - .env 不进镜像（含密钥），由 compose 的 env_file 注入
#   - 时区与编码统一，避免容器内时间/中文乱码

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai \
    LANG=C.UTF-8

WORKDIR /app

# curl 供 HEALTHCHECK 使用；tzdata 保证时区生效
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl tzdata \
    && rm -rf /var/lib/apt/lists/*

# 先单独拷贝依赖清单，利用镜像层缓存：只改代码时不必重装依赖
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
