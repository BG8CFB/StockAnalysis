"""
股票分析平台 - 后端主入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.admin.api import router as core_admin_router
from core.admin.tasks import init_scheduler, shutdown_scheduler
from core.config import settings
from core.db.mongodb import close_mongodb, connect_to_mongodb
from core.db.redis import close_redis, connect_to_redis
from core.exceptions import setup_exception_handlers
from core.logging_config import setup_logging
from core.settings.api import router as settings_router
from core.user.api import router as user_router
from core.system.api import router as system_router
from modules.analysis.api import router as analysis_router
from modules.task_center.api import router as task_center_router
from modules.screener.api import router as screener_router
from modules.ask_stock.api import router as ask_stock_router

# 初始化日志系统
setup_logging()

import logging
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    logger.info(f"正在启动 {settings.APP_NAME} v{settings.APP_VERSION}...")
    logger.info(f"运行模式: {'开发环境' if settings.DEBUG else '生产环境'}")

    await connect_to_mongodb()
    logger.info("MongoDB 连接成功")

    await connect_to_redis()
    logger.info("Redis 连接成功")

    init_scheduler()  # 启动定时任务调度器
    logger.info("定时任务调度器已初始化")

    logger.info(f"{settings.APP_NAME} 启动完成")

    yield

    # 关闭
    logger.info(f"正在关闭 {settings.APP_NAME}...")
    shutdown_scheduler()  # 关闭定时任务调度器
    await close_mongodb()
    await close_redis()
    logger.info(f"{settings.APP_NAME} 已关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="股票分析平台 API",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # 异常处理
    setup_exception_handlers(app)

    # 注册路由（按优先级）
    # 核心路由（新架构）
    app.include_router(settings_router, prefix=settings.API_V1_PREFIX)  # 系统设置
    app.include_router(core_admin_router, prefix=settings.API_V1_PREFIX) # 核心管理员
    
    # 基础设施路由
    app.include_router(system_router, prefix=settings.API_V1_PREFIX)    # 系统管理
    app.include_router(user_router, prefix=settings.API_V1_PREFIX)      # 用户管理
    
    # 业务模块路由
    app.include_router(analysis_router, prefix=settings.API_V1_PREFIX)
    app.include_router(task_center_router, prefix=settings.API_V1_PREFIX)
    app.include_router(screener_router, prefix=settings.API_V1_PREFIX)
    app.include_router(ask_stock_router, prefix=settings.API_V1_PREFIX)

    # 健康检查
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": settings.APP_VERSION}

    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
        }

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
