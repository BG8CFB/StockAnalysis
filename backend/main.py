"""
股票分析平台 - FastAPI 主应用入口

"""

import asyncio
import io
import locale
import logging
import sys

# ==================== Windows UTF-8 编码修复 ====================
# 在 Windows 系统上，默认控制台编码为 GBK，无法正确显示 emoji 字符
# 这里强制使用 UTF-8 编码，避免 'gbk' codec can't encode character 错误
if sys.platform == "win32":
    # 设置标准输出流为 UTF-8
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    # 设置默认编码为 UTF-8
    if hasattr(locale, "getencoding"):
        locale.getencoding = lambda: "utf-8"
# ================================================================

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from core.admin.tasks import init_scheduler, shutdown_scheduler
from core.config import settings
from core.db.mongodb import close_mongodb, connect_to_mongodb
from core.db.redis import close_redis, connect_to_redis
from core.logging_config import setup_logging

# ==================== 配置日志系统 ====================
# 在导入其他模块之前配置日志，确保所有模块的日志都能正常输出
setup_logging(level=settings.LOG_LEVEL)
# ================================================================
from core.market_data.repositories.stock_financial import (  # noqa: E402
    StockFinancialIndicatorRepository,
    StockFinancialRepository,
)
from core.market_data.repositories.stock_info import StockInfoRepository  # noqa: E402
from core.market_data.repositories.stock_quotes import StockQuoteRepository  # noqa: E402
from core.market_data.services.data_scheduler import get_data_scheduler  # noqa: E402
from core.market_data.services.data_sync_service import DataSyncService  # noqa: E402
from core.market_data.services.startup_data_service import StartupDataService  # noqa: E402

# 配置彩色日志
logger = logging.getLogger(__name__)

# 保存后台 Task 引用，防止被垃圾回收器提前回收
_background_tasks: set = set()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    应用生命周期管理

    启动阶段：初始化所有服务
    关闭阶段：清理所有资源
    """
    # ==================== 启动阶段 ====================
    logger.info("=" * 60)
    logger.info("🚀 启动股票分析平台")
    logger.info("=" * 60)

    try:
        # 1. 初始化 MongoDB
        logger.info("📦 初始化 MongoDB...")
        await connect_to_mongodb()
        logger.info("✅ MongoDB 连接成功")

        # 2. 初始化 Redis
        logger.info("📦 初始化 Redis...")
        await connect_to_redis()
        logger.info("✅ Redis 连接成功")

        # 3. 初始化数据库索引
        logger.info("📦 初始化数据库索引...")
        await init_database_indexes()
        logger.info("✅ 数据库索引初始化完成")

        # 4. 初始化系统配置
        logger.info("📦 初始化系统配置...")
        await init_system_config()
        logger.info("✅ 系统配置初始化完成")

        # 5. 启动定时任务调度器
        logger.info("📦 启动定时任务调度器...")
        init_scheduler()
        logger.info("✅ 定时任务调度器启动成功")

        # 6. 清理并发控制状态（防止死锁）
        logger.info("📦 清理并发控制状态...")
        from modules.trading_agents.manager.concurrency_controller import get_concurrency_controller

        concurrency_controller = get_concurrency_controller()
        await concurrency_controller.cleanup_on_startup()
        logger.info("✅ 并发控制状态已清理")

        # 7. 初始化 WebSocket 管理器（需在事件循环就绪后启动清理任务）
        logger.info("📦 初始化 WebSocket 管理器...")
        from modules.trading_agents.api.websocket_manager import websocket_manager

        await websocket_manager.initialize()
        logger.info("✅ WebSocket 管理器初始化完成")

        # 8. 从数据库刷新 MCP 配置缓存（确保用户配置生效）
        logger.info("📦 加载 MCP 数据库配置...")
        from core.mcp.config.loader import refresh_mcp_config_from_db

        await refresh_mcp_config_from_db()
        logger.info("✅ MCP 配置已从数据库加载")

        # 9. 启动市场数据定时调度器
        await init_market_data_scheduler()

        logger.info("=" * 60)
        logger.info("🎉 所有服务启动完成！")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 启动失败: {e}", exc_info=True)
        raise

    yield

    # ==================== 关闭阶段 ====================
    logger.info("=" * 60)
    logger.info("🛑 关闭股票分析平台")
    logger.info("=" * 60)

    try:
        # 1. 关闭定时任务调度器
        logger.info("📦 关闭定时任务调度器...")
        shutdown_scheduler()
        logger.info("✅ 定时任务调度器已关闭")

        # 2. 关闭市场数据定时调度器
        await shutdown_market_data_scheduler()

        # 3. 关闭 Redis 连接
        logger.info("📦 关闭 Redis 连接...")
        await close_redis()
        logger.info("✅ Redis 连接已关闭")

        # 3. 关闭 MongoDB 连接
        logger.info("📦 关闭 MongoDB 连接...")
        await close_mongodb()
        logger.info("✅ MongoDB 连接已关闭")

        logger.info("=" * 60)
        logger.info("✅ 所有服务已安全关闭")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 关闭过程中发生错误: {e}", exc_info=True)


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用

    Returns:
        FastAPI: 配置好的应用实例
    """
    # 创建 FastAPI 应用
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="基于 LangGraph 的股票分析平台",
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # ==================== 请求日志中间件 ====================
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Any) -> Response:
        """记录所有 HTTP 请求"""
        import time

        start_time = time.time()

        # 记录请求
        logger.info(f"➡️  {request.method} {request.url.path}")

        try:
            response: Response = await call_next(request)

            # 计算处理时间
            process_time = (time.time() - start_time) * 1000
            status = response.status_code

            # 记录响应
            log_func = logger.warning if status >= 400 else logger.info
            log_func(f"⬅️  {request.method} {request.url.path} - {status} ({process_time:.0f}ms)")

            return response
        except Exception as e:
            # 记录异常
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"❌ {request.method} {request.url.path} - 异常: {e} ({process_time:.0f}ms)"
            )
            raise

    # ==================== 注册路由 ====================
    # 注意：注册顺序很重要！核心路由优先，业务模块在后

    # 核心设置路由
    # 核心管理路由
    from core.admin.api import router as core_admin_router

    # AI 核心路由
    from core.ai.api import router as ai_core_router
    from core.api_compat.analysis_router import (
        router as analysis_router,
    )
    from core.api_compat.analysis_router import (
        stream_router as analysis_stream_router,
    )

    # 配置兼容路由（前端 /api/config/* 端点）
    from core.api_compat.config_router import router as config_compat_router
    from core.api_compat.reports_router import router as reports_router
    from core.favorites.api import router as favorites_router
    from core.market_data.admin_api import router as market_data_router
    from core.mcp.api.routes import router as mcp_router
    from core.settings.api.admin import router as admin_settings_router
    from core.settings.api.system import router as system_settings_router
    from core.settings.api.user import router as user_settings_router

    # 股票数据查询路由
    from core.stock_data.api import stock_data_router, stocks_router

    # 数据同步 & 自选股
    from core.sync.api import router as sync_router

    # 系统路由
    from core.system.api import router as system_router
    from core.system.data_source_status import router as data_source_status_router

    # 用户路由
    from core.user.api import router as user_router
    from modules.ask_stock.api import router as ask_stock_router

    # 业务模块路由
    from modules.screener.api import router as screener_router
    from modules.trading_agents.admin_api import router as trading_agents_admin_router
    from modules.trading_agents.api import router as trading_agents_router

    # 注册所有路由（按优先级顺序）
    app.include_router(system_settings_router, prefix="/api")
    app.include_router(admin_settings_router, prefix="/api")
    app.include_router(core_admin_router, prefix="/api")
    app.include_router(ai_core_router, prefix="/api")
    app.include_router(system_router, prefix="/api")
    app.include_router(data_source_status_router, prefix="/api")
    app.include_router(user_router, prefix="/api")
    app.include_router(user_settings_router, prefix="/api")
    app.include_router(screener_router, prefix="/api")
    app.include_router(ask_stock_router, prefix="/api")
    app.include_router(mcp_router, prefix="/api")
    app.include_router(trading_agents_router, prefix="/api")
    app.include_router(trading_agents_admin_router, prefix="/api")
    app.include_router(market_data_router, prefix="/api")
    app.include_router(config_compat_router, prefix="/api")
    app.include_router(stocks_router, prefix="/api")
    app.include_router(stock_data_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")

    # 筛选 & 多市场查询路由
    from core.multi_market.api import router as multi_market_router
    from core.screening.api import router as screening_router

    app.include_router(screening_router, prefix="/api")
    app.include_router(multi_market_router, prefix="/api")

    # 数据同步 & 自选股
    app.include_router(sync_router, prefix="/api")
    app.include_router(favorites_router, prefix="/api")

    # 系统管理模块（调度器、缓存、数据库、日志、用量、工具）
    from core.cache.api import router as cache_router
    from core.database_admin.api import router as database_admin_router
    from core.operation_logs.api import router as operation_logs_router
    from core.scheduler.api import router as scheduler_router
    from core.system_logs.api import router as system_logs_router
    from core.tools.api import router as tools_router
    from core.usage.api import router as usage_router

    app.include_router(scheduler_router, prefix="/api")
    app.include_router(cache_router, prefix="/api")
    app.include_router(database_admin_router, prefix="/api")
    app.include_router(system_logs_router, prefix="/api")
    app.include_router(operation_logs_router, prefix="/api")
    app.include_router(usage_router, prefix="/api")
    app.include_router(tools_router, prefix="/api")

    # API 兼容层路由
    app.include_router(analysis_router, prefix="/api")
    app.include_router(analysis_stream_router, prefix="/api")

    logger.info("✅ 所有路由已注册")

    # ==================== 全局异常处理 ====================
    from core.exceptions import setup_exception_handlers

    setup_exception_handlers(app)
    logger.info("✅ 全局异常处理器已注册")

    # ==================== 健康检查端点 ====================

    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        """健康检查端点"""
        return {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    return app


async def init_database_indexes() -> None:
    """
    初始化所有数据库索引

    为所有集合创建必要的索引以优化查询性能
    """
    # 市场数据模块索引
    stock_info_repo = StockInfoRepository()
    await stock_info_repo.init_indexes()

    stock_quotes_repo = StockQuoteRepository()
    await stock_quotes_repo.init_indexes()

    stock_financials_repo = StockFinancialRepository()
    await stock_financials_repo.init_indexes()

    stock_indicators_repo = StockFinancialIndicatorRepository()
    await stock_indicators_repo.init_indexes()

    # 自选股模块索引
    from core.favorites.service import FavoriteRepository

    favorites_repo = FavoriteRepository()
    await favorites_repo.ensure_indexes()

    logger.info("✅ 市场数据模块索引创建完成")


async def init_system_config() -> None:
    """
    初始化系统配置

    在应用启动时自动初始化系统级配置，确保配置始终可用。
    包括 TradingAgents 全局配置等。
    """
    # 初始化 TradingAgents 全局配置
    from core.settings.services.global_trading_agents_service import ensure_default_config

    try:
        created = await ensure_default_config()
        if created:
            logger.info("✅ TradingAgents 全局配置已创建")
        else:
            logger.info("ℹ️ TradingAgents 全局配置已存在")
    except Exception as e:
        logger.error(f"❌ 初始化 TradingAgents 全局配置失败: {e}")
        # 不抛出异常，允许系统继续启动


# ==================== 市场数据定时调度器 ====================

_market_data_scheduler = None
_data_sync_service = None


async def init_default_data_sources() -> None:
    """
    初始化默认数据源配置

    在应用启动时自动创建默认的系统数据源配置，避免手动配置。
    """
    from core.market_data.config.service import DataSourceConfigService
    from core.market_data.repositories.datasource import SystemDataSourceRepository

    logger.info("📦 初始化默认数据源配置...")

    try:
        config_service = DataSourceConfigService()
        system_repo = SystemDataSourceRepository()

        # 检查是否已有配置
        existing_configs = await system_repo.find_many({})
        if len(existing_configs) > 0:
            logger.info(f"✅ 数据源配置已存在 ({len(existing_configs)} 条)，跳过初始化")
            return

        # 定义默认数据源配置
        default_sources: list[dict[str, Any]] = [
            # A股数据源
            {
                "source_id": "akshare",
                "market": "A_STOCK",
                "enabled": True,
                "priority": 1,
                "config": {},
                "rate_limit": {"requests_per_minute": 100},
                "supported_data_types": [
                    "stock_list",
                    "daily_quotes",
                    "minute_quotes",
                    "financials",
                    "company_info",
                    "sector",
                    "macro_economy",
                    "news",
                    "calendar",
                ],
            },
            {
                "source_id": "tushare",
                "market": "A_STOCK",
                "enabled": True,
                "priority": 2,
                "config": {"api_token": ""},  # 需要用户配置
                "rate_limit": {"requests_per_minute": 200},
                "supported_data_types": [
                    "stock_list",
                    "daily_quotes",
                    "financials",
                    "company_info",
                    "macro_economy",
                    "adj_factor",
                ],
            },
            # 美股数据源
            {
                "source_id": "yahoo",
                "market": "US_STOCK",
                "enabled": True,
                "priority": 1,
                "config": {},
                "rate_limit": {"requests_per_minute": 100},
                "supported_data_types": [
                    "daily_quotes",
                    "minute_quotes",
                    "financials",
                    "company_info",
                    "news",
                    "calendar",
                    "macro_economy",
                    "sector",
                    "index",
                ],
            },
            {
                "source_id": "alpha_vantage",
                "market": "US_STOCK",
                "enabled": False,  # 默认禁用，需要API Key
                "priority": 2,
                "config": {"api_key": ""},
                "rate_limit": {"requests_per_minute": 5},
                "supported_data_types": ["daily_quotes", "financials", "macro_economy"],
            },
            # 港股数据源
            {
                "source_id": "yahoo",
                "market": "HK_STOCK",
                "enabled": True,
                "priority": 1,
                "config": {},
                "rate_limit": {"requests_per_minute": 100},
                "supported_data_types": [
                    "daily_quotes",
                    "minute_quotes",
                    "company_info",
                    "news",
                    "calendar",
                    "margin",
                ],
            },
            {
                "source_id": "akshare",
                "market": "HK_STOCK",
                "enabled": True,
                "priority": 2,
                "config": {},
                "rate_limit": {"requests_per_minute": 100},
                "supported_data_types": ["daily_quotes", "financials"],
            },
        ]

        # 创建配置
        for source_config in default_sources:
            try:
                await config_service.create_system_source(**source_config)
                logger.info(
                    f"  ✅ 创建数据源配置: {source_config['source_id']} ({source_config['market']})"
                )
            except Exception as e:
                logger.warning(f"  ⚠️ 创建数据源配置失败: {source_config['source_id']} - {e}")

        logger.info(f"✅ 默认数据源配置初始化完成 ({len(default_sources)} 条)")

    except Exception as e:
        logger.error(f"❌ 初始化默认数据源配置失败: {e}", exc_info=True)
        # 不抛出异常，允许应用继续启动


async def _run_startup_check(startup_service: StartupDataService) -> None:
    """后台执行启动检查"""
    try:
        catchup_result = await startup_service.check_and_catchup()

        if catchup_result.get("is_first_startup"):
            logger.info("✅ 首次启动数据同步完成")
        else:
            tasks_count = len(catchup_result.get("tasks_triggered", []))
            if tasks_count > 0:
                logger.info(f"✅ 启动数据补录完成，触发 {tasks_count} 个补录任务")
            else:
                logger.info("✅ 数据完整性检查通过，无需补录")

        # 启动健康检查后台任务（并行执行，不阻塞启动）
        health_check_tasks = catchup_result.get("health_check_tasks", [])
        if health_check_tasks:
            logger.info(f"📊 启动后台健康检查任务，共 {len(health_check_tasks)} 个检查项...")
            # 使用 create_task 在后台并行执行健康检查
            _task = asyncio.create_task(_run_health_checks(startup_service, health_check_tasks))
            _background_tasks.add(_task)
            _task.add_done_callback(_background_tasks.discard)

    except Exception as e:
        logger.error(f"❌ 后台启动检查任务失败: {e}", exc_info=True)


async def _run_health_checks(
    startup_service: StartupDataService, health_check_tasks: list[Any]
) -> None:
    """后台并行执行健康检查"""
    logger.info("=" * 60)
    logger.info("🚀 启动后台健康检查任务")
    logger.info(f"📋 待检查项: {len(health_check_tasks)} 个")
    logger.info("ℹ️ 健康检查在后台执行，不阻塞应用启动")
    logger.info("=" * 60)

    try:
        result = await startup_service.run_health_checks_parallel(health_check_tasks)
        logger.info("=" * 60)
        logger.info("🎉 后台健康检查全部完成")
        logger.info(
            f"📊 统计: 总计 {result['total']} 个，"
            f"✅ 通过 {result['passed']} 个，"
            f"❌ 失败 {result['failed']} 个"
        )
        logger.info("=" * 60)
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ 后台健康检查任务失败: {e}")
        logger.error("=" * 60, exc_info=True)


async def init_market_data_scheduler() -> None:
    """初始化市场数据定时调度器"""
    global _market_data_scheduler, _data_sync_service

    try:
        logger.info("📦 初始化市场数据定时调度器...")

        # 0. 初始化默认数据源配置（新增）
        await init_default_data_sources()

        # 创建数据同步服务
        _data_sync_service = DataSyncService()

        # 获取调度器实例
        _market_data_scheduler = get_data_scheduler()

        # 设置数据同步服务
        _market_data_scheduler.set_data_sync_service(_data_sync_service)

        # 调度所有任务
        _market_data_scheduler.schedule_all_jobs()

        # 启动调度器
        _market_data_scheduler.start()

        logger.info("✅ 市场数据定时调度器启动成功")

        # 输出已调度的任务
        jobs = _market_data_scheduler.get_scheduled_jobs()
        logger.info(f"已调度 {len(jobs)} 个市场数据同步任务:")
        for job in jobs:
            logger.info(f"  - {job['name']}: 下次执行时间 {job['next_run_time']}")

        # 启动时数据检查和补录（异步后台执行，不阻塞启动）
        logger.info("📊 启动后台数据检查和补录任务（异步）...")
        startup_service = StartupDataService(_data_sync_service)
        # 使用 create_task 在后台运行，不阻塞主程序启动（保存引用防止垃圾回收）
        _task = asyncio.create_task(_run_startup_check(startup_service))
        _background_tasks.add(_task)
        _task.add_done_callback(_background_tasks.discard)

    except Exception as e:
        logger.error(f"❌ 市场数据定时调度器启动失败: {e}", exc_info=True)
        raise


async def shutdown_market_data_scheduler() -> None:
    """关闭市场数据定时调度器"""
    global _market_data_scheduler, _data_sync_service

    try:
        if _market_data_scheduler:
            logger.info("📦 关闭市场数据定时调度器...")
            _market_data_scheduler.shutdown()
            _market_data_scheduler = None
            logger.info("✅ 市场数据定时调度器已关闭")

        _data_sync_service = None

    except Exception as e:
        logger.error(f"❌ 关闭市场数据定时调度器失败: {e}", exc_info=True)


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
