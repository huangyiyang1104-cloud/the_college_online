"""统一业务异常与响应包装。

约定（见 04.API接口设计.md）：
  成功  {"code": 0, "message": "ok", "data": ...}
  失败  {"code": 4xxxx, "message": "...", "data": {"fields": [...]}}，HTTP 状态码表达语义
"""

from typing import Any

from fastapi.responses import JSONResponse


class api_error(Exception):
    """业务异常：由全局处理器统一转成标准响应，路由里不再写 try/except。"""

    def __init__(
        self,
        code: int,
        message: str,
        http_status: int = 400,
        fields: list[dict[str, str]] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        self.fields = fields or []
        super().__init__(message)


# ---- 常用错误构造 ----
def param_error(message: str = "参数校验失败", fields: list[dict[str, str]] | None = None) -> api_error:
    return api_error(10001, message, 400, fields)


def unauthorized(message: str = "未认证或登录已失效") -> api_error:
    return api_error(10002, message, 401)


def forbidden(message: str = "无权限执行该操作") -> api_error:
    return api_error(10003, message, 403)


def not_found(message: str = "资源不存在") -> api_error:
    return api_error(10004, message, 404)


def conflict(message: str = "状态冲突", code: int = 10005) -> api_error:
    return api_error(code, message, 409)


def ok(data: Any = None) -> dict[str, Any]:
    return {"code": 0, "message": "ok", "data": data}


def paged(items: list[Any], total: int, page: int, page_size: int) -> dict[str, Any]:
    return {"list": items, "total": total, "page": page, "page_size": page_size}


def error_response(exc: api_error) -> JSONResponse:
    payload: dict[str, Any] = {"code": exc.code, "message": exc.message, "data": None}
    if exc.fields:
        payload["data"] = {"fields": exc.fields}
    return JSONResponse(status_code=exc.http_status, content=payload)
