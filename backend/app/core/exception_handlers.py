"""外部服务错误的统一 HTTP 响应。"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.tools.github.errors import GitHubAPIError


async def github_error_handler(_: Request, error: GitHubAPIError) -> JSONResponse:
    """返回可解释错误，但不暴露请求头、Token 或内部堆栈。"""
    status_code = error.status_code if error.status_code is not None else 502
    content: dict[str, Any] = {
        "detail": error.message,
        "code": error.code,
        "retryable": error.retryable,
    }
    if error.rate_limit_reset is not None:
        content["rate_limit_reset"] = error.rate_limit_reset
    return JSONResponse(status_code=status_code, content=content)


def register_exception_handlers(app: FastAPI) -> None:
    """集中注册应用级异常处理器。"""
    app.add_exception_handler(GitHubAPIError, github_error_handler)  # type: ignore[arg-type]

