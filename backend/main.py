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
from core.ai.api import router as ai_core_router
from modules.analysis.api import router as analysis_router
from modules.task_center.api import router as task_center_router
from modules.screener.api import router as screener_router
from modules.ask_stock.api import router as ask_stock_router
from modules.trading_agents.api import router as trading_agents_router
from modules.trading_agents.admin_api import router as trading_agents_admin_router

# 初始化日志系统
setup_logging()

import logging
logger = logging.getLogger(__name__)


# 应用 MCP Python SDK Bug 补丁
# 修复：空 SSE 数据导致 ValidationError（Issue #1672）
# 参考：https://github.com/modelcontextprotocol/python-sdk/issues/1672
try:
    from modules.trading_agents.services.mcp_patch import apply_mcp_patches
    apply_mcp_patches()
except Exception as e:
    logger.warning(f"MCP 补丁应用失败: {e}")


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

    # 启动 TradingAgents 后台任务
    from modules.trading_agents.core.task_expiry import start_expiry_handler
    from modules.trading_agents.services.report_archival import start_archival_service
    try:
        await start_expiry_handler()
        logger.info("TradingAgents 任务过期处理器已启动")
    except Exception as e:
        logger.warning(f"TradingAgents 任务过期处理器启动失败: {e}")

    try:
        await start_archival_service()
        logger.info("TradingAgents 报告归档服务已启动")
    except Exception as e:
        logger.warning(f"TradingAgents 报告归档服务启动失败: {e}")

    # 启动任务队列
    from modules.trading_agents.core.task_queue import start_task_queue
    try:
        await start_task_queue()
        logger.info("TradingAgents 任务队列已启动")
    except Exception as e:
        logger.warning(f"TradingAgents 任务队列启动失败: {e}")

    # 初始化 TradingAgents 模块数据库索引
    from modules.trading_agents.core.database import init_indexes
    try:
        await init_indexes()
        logger.info("TradingAgents 数据库索引初始化成功")
    except Exception as e:
        logger.warning(f"TradingAgents 数据库索引初始化失败: {e}")

    # 恢复运行中的任务
    from modules.trading_agents.core.task_manager import get_task_manager
    try:
        task_manager = get_task_manager()
        restored_count = await task_manager.restore_running_tasks()
        if restored_count > 0:
            logger.info(f"TradingAgents 任务恢复完成，共恢复 {restored_count} 个任务")
    except Exception as e:
        logger.warning(f"TradingAgents 任务恢复失败: {e}")

    # 初始化智能体公共配置
    from modules.trading_agents.services.agent_config_service import get_agent_config_service
    try:
        service = get_agent_config_service()
        await service.ensure_public_config_exists()
        logger.info("TradingAgents 公共配置已初始化")
    except Exception as e:
        logger.warning(f"TradingAgents 公共配置初始化失败: {e}")

    # 启动 MCP 健康检查器和会话管理器
    from modules.trading_agents.services.mcp_health_checker import get_mcp_health_checker
    from modules.trading_agents.services.mcp_session_manager import get_mcp_session_manager
    try:
        health_checker = get_mcp_health_checker()
        await health_checker.start()
        logger.info("MCP 健康检查器已启动")
    except Exception as e:
        logger.warning(f"MCP 健康检查器启动失败: {e}")

    try:
        session_manager = get_mcp_session_manager()
        await session_manager.start()
        logger.info("MCP 会话管理器已启动")
    except Exception as e:
        logger.warning(f"MCP 会话管理器启动失败: {e}")

    logger.info(f"{settings.APP_NAME} 启动完成")

    yield

    # 关闭
    logger.info(f"正在关闭 {settings.APP_NAME}...")
    shutdown_scheduler()  # 关闭定时任务调度器

    # 停止 TradingAgents 后台任务
    from modules.trading_agents.core.task_expiry import stop_expiry_handler
    from modules.trading_agents.services.report_archival import stop_archival_service
    try:
        await stop_expiry_handler()
    except Exception as e:
        logger.warning(f"TradingAgents 任务过期处理器停止失败: {e}")

    try:
        await stop_archival_service()
    except Exception as e:
        logger.warning(f"TradingAgents 报告归档服务停止失败: {e}")

    # 停止任务队列
    from modules.trading_agents.core.task_queue import stop_task_queue
    try:
        await stop_task_queue()
    except Exception as e:
        logger.warning(f"TradingAgents 任务队列停止失败: {e}")

    # 停止 MCP 健康检查器和会话管理器
    from modules.trading_agents.services.mcp_health_checker import get_mcp_health_checker
    from modules.trading_agents.services.mcp_session_manager import get_mcp_session_manager
    try:
        health_checker = get_mcp_health_checker()
        await health_checker.stop()
        logger.info("MCP 健康检查器已停止")
    except Exception as e:
        logger.warning(f"MCP 健康检查器停止失败: {e}")

    try:
        session_manager = get_mcp_session_manager()
        await session_manager.stop()
        logger.info("MCP 会话管理器已停止")
    except Exception as e:
        logger.warning(f"MCP 会话管理器停止失败: {e}")

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
    app.include_router(ai_core_router, prefix=settings.API_V1_PREFIX)    # AI 核心模块

    # 基础设施路由
    app.include_router(system_router, prefix=settings.API_V1_PREFIX)    # 系统管理
    app.include_router(user_router, prefix=settings.API_V1_PREFIX)      # 用户管理

    # 业务模块路由
    app.include_router(analysis_router, prefix=settings.API_V1_PREFIX)
    app.include_router(task_center_router, prefix=settings.API_V1_PREFIX)
    app.include_router(screener_router, prefix=settings.API_V1_PREFIX)
    app.include_router(ask_stock_router, prefix=settings.API_V1_PREFIX)
    app.include_router(trading_agents_router, prefix=settings.API_V1_PREFIX)
    app.include_router(trading_agents_admin_router, prefix=settings.API_V1_PREFIX)  # TradingAgents 管理员 API

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
