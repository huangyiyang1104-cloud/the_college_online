"""云枢智学 · 后端入口（本阶段：管理端接口）。"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.admin import admin_router
from app.api.student import student_router
from app.core.config import settings_cache
from app.core.db import session_factory
from app.core.errors import api_error, error_response, ok
from app.core.security import hash_password
from app.models import admin_user

logger = logging.getLogger("yunshu")

app = FastAPI(
    title="云枢智学 API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_cache.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router, prefix="/api/v1")
app.include_router(student_router, prefix="/api/v1")


@app.get("/api/v1/health")
def health():
    return ok({"status": "up", "env": settings_cache.app_env})


@app.exception_handler(api_error)
async def handle_api_error(request: Request, exc: api_error) -> JSONResponse:
    return error_response(exc)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [
        {"field": ".".join(str(part) for part in item["loc"][1:]), "reason": item["msg"]}
        for item in exc.errors()
    ]
    return error_response(api_error(10001, "参数校验失败", 400, fields))


@app.exception_handler(Exception)
async def handle_unknown_error(request: Request, exc: Exception) -> JSONResponse:
    # 不把堆栈与 SQL 细节返回给前端（见开发规范第 12 条）
    logger.exception("unhandled error: %s", exc)
    return error_response(api_error(10007, "服务内部错误，请稍后重试", 500))


@app.on_event("startup")
def seed_builtin_admin() -> None:
    """首次启动创建内置超管，避免空库无法登录。"""
    with session_factory() as db:
        exists = db.execute(select(admin_user.id).limit(1)).first()
        if exists:
            return
        db.add(
            admin_user(
                username="admin",
                password_hash=hash_password("admin123"),
                role=1,
                is_builtin=1,
                status=1,
            )
        )
        db.commit()
        logger.warning("已创建内置超管 admin / admin123，请登录后立即修改密码")
