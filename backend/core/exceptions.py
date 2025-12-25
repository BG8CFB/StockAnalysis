"""
全局异常处理
"""
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器"""
    # 记录未处理的异常
    logger.error(
        f"未处理的异常: path={request.url.path}, method={request.method}, "
        f"exc_type={type(exc).__name__}, exc_msg={str(exc)}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误",
                "details": str(exc) if request.app.debug else None,
            },
        },
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """设置异常处理器"""
    app.add_exception_handler(Exception, global_exception_handler)
