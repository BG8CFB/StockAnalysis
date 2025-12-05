from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)


class TradingAgentsException(Exception):
    """自定义异常基类"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ModuleException(TradingAgentsException):
    """模块相关异常"""
    pass


class AuthenticationException(TradingAgentsException):
    """认证相关异常"""
    pass


class DatabaseException(TradingAgentsException):
    """数据库相关异常"""
    pass


class ValidationException(TradingAgentsException):
    """验证相关异常"""
    pass


async def tradingagents_exception_handler(request: Request, exc: TradingAgentsException):
    """自定义异常处理器"""
    logger.error(f"TradingAgents exception: {exc.message}")

    return JSONResponse(
        status_code=500,
        content={
            "error": "TradingAgents Error",
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "path": str(request.url.path)
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path)
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """验证异常处理器"""
    logger.warning(f"Validation exception: {exc.errors()}")

    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "Invalid request data",
            "details": exc.errors(),
            "path": str(request.url.path)
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "error_type": type(exc).__name__,
            "path": str(request.url.path)
        }
    )


def setup_exception_handlers(app: FastAPI):
    """设置全局异常处理器"""
    app.add_exception_handler(TradingAgentsException, tradingagents_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Exception handlers configured")