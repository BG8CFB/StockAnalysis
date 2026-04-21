"""
数据库初始化模块

所有"部署时初始化一次"的数据库逻辑统一放在这里。
包含：索引创建、默认数据、系统配置等。
每个初始化函数都有自己的防重复检查，可安全地在每次启动时调用。
"""

import logging
from datetime import datetime, timezone
from typing import Any

from core.auth.rbac import Role
from core.auth.security import password_manager
from core.db.mongodb import mongodb
from core.user.models import UserStatus

logger = logging.getLogger(__name__)


async def _init_core_indexes() -> None:
    """初始化核心集合索引（users, user_preferences）"""
    db = mongodb.database

    # 用户集合索引
    await db.users.create_index("email", unique=True)
    await db.users.create_index("created_at")

    # 用户配置集合索引
    await db.user_preferences.create_index([("user_id", 1)], unique=False)
    await db.user_preferences.create_index([("user_id", 1), ("key", 1)], unique=True)

    logger.debug("核心索引初始化完成")


async def _init_repository_indexes() -> None:
    """初始化所有业务仓库的集合索引"""
    # 市场数据模块索引
    from core.market_data.repositories.stock_info import StockInfoRepository
    from core.market_data.repositories.stock_quotes import StockQuoteRepository
    from core.market_data.repositories.stock_financial import (
        StockFinancialRepository,
        StockFinancialIndicatorRepository,
    )

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

    # 公司信息索引
    from core.market_data.repositories.stock_company import StockCompanyRepository

    stock_company_repo = StockCompanyRepository()
    await stock_company_repo.create_indexes()

    # 宏观经济索引
    from core.market_data.repositories.macro_economic import MacroEconomicRepository

    macro_repo = MacroEconomicRepository()
    await macro_repo.create_indexes()

    # 市场新闻索引
    from core.market_data.repositories.market_news import MarketNewsRepository

    news_repo = MarketNewsRepository()
    await news_repo.create_indexes()

    # 数据源模块索引（系统数据源、用户数据源、数据源状态、状态历史）
    from core.market_data.repositories.datasource import (
        SystemDataSourceRepository,
        UserDataSourceRepository,
        DataSourceStatusRepository,
        DataSourceStatusHistoryRepository,
    )

    system_ds_repo = SystemDataSourceRepository()
    await system_ds_repo.create_indexes()

    user_ds_repo = UserDataSourceRepository()
    await user_ds_repo.create_indexes()

    ds_status_repo = DataSourceStatusRepository()
    await ds_status_repo.create_indexes()

    ds_history_repo = DataSourceStatusHistoryRepository()
    await ds_history_repo.create_indexes()

    # TradingAgents 模块索引
    from modules.trading_agents.manager.database import init_indexes as init_ta_indexes

    await init_ta_indexes()

    # TradingAgents 用户设置索引
    from modules.trading_agents.manager.settings_service import TradingAgentsSettingsService

    ta_settings = TradingAgentsSettingsService()
    await ta_settings.ensure_index()

    # 用户配置索引
    from core.settings.services.user_service import init_user_settings_indexes

    await init_user_settings_indexes()

    logger.info("✅ 所有数据库索引创建完成")


async def _init_default_users() -> None:
    """
    初始化默认管理员用户

    首次部署时自动创建默认管理员账号（admin / admin123）。
    如果数据库中已存在用户，则跳过创建。
    """
    db = mongodb.database

    # 检查是否已有用户
    user_count = await db.users.count_documents({})
    if user_count > 0:
        logger.info(f"ℹ️ 数据库中已有 {user_count} 个用户，跳过默认用户创建")
        return

    # 创建默认管理员
    hashed_password = password_manager.hash_password("admin123")
    admin_doc = {
        "email": "admin@stockanalysis.com",
        "username": "admin",
        "hashed_password": hashed_password,
        "role": Role.SUPER_ADMIN,
        "status": UserStatus.ACTIVE,
        "is_active": True,
        "is_verified": True,
        "created_by": None,
        "last_login_at": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = await db.users.insert_one(admin_doc)
    logger.info(f"✅ 默认管理员已创建: admin / admin123 (ID: {result.inserted_id})")


async def _init_system_configs() -> None:
    """
    初始化系统配置

    包括 TradingAgents 全局配置等。
    """
    from core.settings.services.global_trading_agents_service import ensure_default_config

    try:
        created = await ensure_default_config()
        if created:
            logger.info("✅ TradingAgents 全局配置已创建")
        else:
            logger.info("ℹ️ TradingAgents 全局配置已存在")
    except Exception as e:
        logger.error(f"❌ 初始化 TradingAgents 全局配置失败: {e}")


async def _init_data_sources() -> None:
    """
    初始化默认数据源配置

    首次部署时自动创建默认的系统数据源配置，避免手动配置。
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
                "config": {"api_token": ""},
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
                "enabled": False,
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


async def run_all_initializers() -> None:
    """
    统一初始化入口

    部署时执行一次，包含：
    1. 核心索引（users, user_preferences）
    2. 所有业务仓库索引（市场数据、自选股、TradingAgents 等）
    3. 默认管理员用户（admin / admin123）
    4. 系统配置（TradingAgents 全局配置）
    5. 数据源配置（A股/美股/港股的默认数据源）

    每个子函数都有自己的防重复检查，可安全地在每次启动时调用。
    """
    logger.info("=" * 60)
    logger.info("🗄️ 开始数据库初始化")
    logger.info("=" * 60)

    await _init_core_indexes()
    await _init_repository_indexes()
    await _init_default_users()
    await _init_system_configs()
    await _init_data_sources()

    logger.info("=" * 60)
    logger.info("✅ 数据库初始化完成")
    logger.info("=" * 60)
