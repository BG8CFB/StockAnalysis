"""
全局异常处理
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from core.config import settings

logger = logging.getLogger(__name__)


def _add_cors_headers(request: Request, response: JSONResponse) -> JSONResponse:
    """为异常响应添加 CORS 头，避免浏览器因 CORS 缺失而报告网络错误"""
    origin = request.headers.get("origin", "")
    if origin and origin in settings.CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    elif "*" in settings.CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = "*"
    return response


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器"""
    # 记录未处理的异常（包含详细信息，仅记录在服务端）
    logger.error(
        f"未处理的异常: path={request.url.path}, method={request.method}, "
        f"exc_type={type(exc).__name__}, exc_msg={str(exc)}",
        exc_info=True,
    )

    # 根据调试模式决定返回给客户端的信息
    if request.app.debug:
        # 调试模式：返回详细错误信息
        error_details = str(exc)
        error_message = f"服务器内部错误: {type(exc).__name__}"
    else:
        # 生产模式：只返回通用错误信息，不泄露任何异常详情
        error_details = None
        error_message = "服务器内部错误，请稍后重试"

    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": error_message,
                "details": error_details,
            },
        },
    )
    return _add_cors_headers(request, response)


def setup_exception_handlers(app: FastAPI) -> None:
    """设置异常处理器"""
    app.add_exception_handler(Exception, global_exception_handler)
