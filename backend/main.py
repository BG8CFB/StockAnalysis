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
if sys.platform == 'win32':
    # 设置标准输出流为 UTF-8
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    # 设置默认编码为 UTF-8
    if hasattr(locale, 'getencoding'):
        locale.getencoding = lambda: 'utf-8'
# ================================================================

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.db.mongodb import mongodb, connect_to_mongodb, close_mongodb
from core.db.redis import redis_manager, connect_to_redis, close_redis
from core.colored_formatter import ColoredFormatter
from core.admin.tasks import init_scheduler, shutdown_scheduler
from core.market_data.repositories.stock_info import StockInfoRepository
from core.market_data.repositories.stock_quotes import StockQuoteRepository
from core.market_data.repositories.stock_financial import (
    StockFinancialRepository,
    StockFinancialIndicatorRepository,
)
from core.market_data.services.data_scheduler import get_data_scheduler
from core.market_data.services.data_sync_service import DataSyncService
from core.market_data.services.startup_data_service import StartupDataService

# 配置彩色日志
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
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

        # 4. 启动定时任务调度器
        logger.info("📦 启动定时任务调度器...")
        init_scheduler()
        logger.info("✅ 定时任务调度器启动成功")

        # 5. 启动市场数据定时调度器
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

    # ==================== 注册路由 ====================
    # 注意：注册顺序很重要！核心路由优先，业务模块在后

    # 核心设置路由
    from core.settings.api.system import router as system_settings_router
    from core.settings.api.user import router as user_settings_router

    # 核心管理路由
    from core.admin.api import router as core_admin_router

    # AI 核心路由
    from core.ai.api import router as ai_core_router

    # 系统路由
    from core.system.api import router as system_router
    from core.system.data_source_status import router as data_source_status_router

    # 用户路由
    from core.user.api import router as user_router

    # 业务模块路由
    from modules.screener.api import router as screener_router
    from modules.ask_stock.api import router as ask_stock_router
    from core.mcp.api.routes import router as mcp_router
    from modules.trading_agents.api import router as trading_agents_router
    from modules.trading_agents.admin_api import router as trading_agents_admin_router
    from core.market_data.admin_api import router as market_data_router

    # 注册所有路由（按优先级顺序）
    app.include_router(system_settings_router, prefix="/api")
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

    logger.info("✅ 所有路由已注册")

    # ==================== 全局异常处理 ====================

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """全局异常处理器"""
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"内部服务器错误: {str(exc)}"},
        )

    # ==================== 健康检查端点 ====================

    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    return app


async def init_database_indexes():
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

    logger.info("✅ 市场数据模块索引创建完成")


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
        default_sources = [
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
                    "daily_quotes", "minute_quotes",
                    "financials", "company_info",
                    "sector", "macro_economy",
                    "news", "calendar"
                ]
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
                    "financials", "company_info",
                    "macro_economy", "adj_factor"
                ]
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
                    "daily_quotes", "minute_quotes",
                    "financials", "company_info",
                    "news", "calendar", "macro_economy", "sector", "index"
                ]
            },
            {
                "source_id": "alpha_vantage",
                "market": "US_STOCK",
                "enabled": False,  # 默认禁用，需要API Key
                "priority": 2,
                "config": {"api_key": ""},
                "rate_limit": {"requests_per_minute": 5},
                "supported_data_types": [
                    "daily_quotes", "financials", "macro_economy"
                ]
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
                    "daily_quotes", "minute_quotes",
                    "company_info", "news", "calendar", "margin"
                ]
            },
            {
                "source_id": "akshare",
                "market": "HK_STOCK",
                "enabled": True,
                "priority": 2,
                "config": {},
                "rate_limit": {"requests_per_minute": 100},
                "supported_data_types": ["daily_quotes", "financials"]
            }
        ]

        # 创建配置
        for source_config in default_sources:
            try:
                await config_service.create_system_source(**source_config)
                logger.info(f"  ✅ 创建数据源配置: {source_config['source_id']} ({source_config['market']})")
            except Exception as e:
                logger.warning(f"  ⚠️ 创建数据源配置失败: {source_config['source_id']} - {e}")

        logger.info(f"✅ 默认数据源配置初始化完成 ({len(default_sources)} 条)")

    except Exception as e:
        logger.error(f"❌ 初始化默认数据源配置失败: {e}", exc_info=True)
        # 不抛出异常，允许应用继续启动


async def _run_startup_check(startup_service: StartupDataService):
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
    except Exception as e:
        logger.error(f"❌ 后台启动检查任务失败: {e}", exc_info=True)


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

        # 执行启动时数据检查和补录（后台运行，不阻塞启动）
        logger.info("📊 启动后台数据检查和补录任务...")
        startup_service = StartupDataService(_data_sync_service)
        # 使用 create_task 在后台运行，不阻塞主程序启动
        asyncio.create_task(_run_startup_check(startup_service))

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
