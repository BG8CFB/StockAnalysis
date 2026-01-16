"""
数据源路由器

实现数据源选择、降级策略和健康检查
"""

import logging
import inspect
from typing import Any
from datetime import datetime

from core.market_data.sources.base import DataSourceAdapter
from core.market_data.sources.a_stock import TuShareAdapter, AkShareAdapter
from core.market_data.sources.us_stock import YahooFinanceAdapter, AlphaVantageAdapter
from core.market_data.sources.hk_stock import YahooHKAdapter, AkShareHKAdapter
from core.market_data.models import MarketType
from core.config import DATA_SOURCE_MAX_FAILURES

logger = logging.getLogger(__name__)


class DataSourceRouter:
    """
    数据源路由器

    负责管理多个数据源，实现自动降级和故障转移
    """

    # 类级别的方法签名缓存，避免重复检查
    _method_signature_cache: dict[str, bool] = {}

    def __init__(self, sources: list[DataSourceAdapter] | None = None):
        """
        初始化路由器

        Args:
            sources: 数据源列表，按优先级排序
        """
        # 按优先级排序数据源
        self.sources = sorted(sources or [], key=lambda s: s.get_priority())
        self.source_health = {}  # 数据源健康状态缓存

    def add_source(self, source: DataSourceAdapter) -> None:
        """
        添加数据源

        Args:
            source: 数据源适配器
        """
        self.sources.append(source)
        # 重新排序
        self.sources.sort(key=lambda s: s.get_priority())

    async def get_available_sources(
        self,
        market: MarketType,
        check_health: bool = True
    ) -> list[DataSourceAdapter]:
        """
        获取指定市场的可用数据源

        Args:
            market: 市场类型
            check_health: 是否检查健康状态

        Returns:
            可用数据源列表（按优先级排序）
        """
        available = []

        for source in self.sources:
            # 检查是否支持该市场
            if not source.supports_market(market):
                continue

            # 检查是否被禁用
            if source.should_disable(max_failures=DATA_SOURCE_MAX_FAILURES):
                logger.warning(f"Data source {source.source_name} is disabled due to repeated failures")
                continue

            # 检查健康状态
            if check_health:
                health = await self._get_source_health(source)
                if not health['is_available']:
                    logger.warning(f"Data source {source.source_name} is not available")
                    continue

            available.append(source)

        return available

    async def route_to_best_source(
        self,
        market: MarketType,
        method_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        路由到最佳可用数据源

        实现自动降级：优先使用优先级高的数据源，失败时自动降级

        Args:
            market: 市场类型
            method_name: 要调用的方法名
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            方法调用结果

        Raises:
            Exception: 所有数据源都失败时抛出异常
        """
        available_sources = await self.get_available_sources(market)

        if not available_sources:
            raise RuntimeError(f"No available data source for market {market}")

        last_error = None

        # 依次尝试可用数据源
        for source in available_sources:
            try:
                logger.info(f"Trying data source: {source.source_name}")

                # 调用数据源方法
                method = getattr(source, method_name)

                # 使用缓存检查方法签名，判断是否需要传递 market 参数
                method_key = f"{source.__class__.__name__}.{method_name}"
                needs_market = DataSourceRouter._method_signature_cache.get(method_key)

                if needs_market is None:
                    sig = inspect.signature(method)
                    params = list(sig.parameters.keys())
                    needs_market = params and params[0] == 'market'
                    DataSourceRouter._method_signature_cache[method_key] = needs_market

                # 根据方法签名调用
                if needs_market:
                    result = await method(market, *args, **kwargs)
                else:
                    result = await method(*args, **kwargs)

                # 成功后重置失败计数
                source.reset_failure_count()

                logger.info(f"Successfully retrieved data from {source.source_name}")
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Failed to get data from {source.source_name}: {e}")
                source.failure_count += 1

                # 如果不是最后一个数据源，继续尝试下一个
                if source != available_sources[-1]:
                    logger.info(f"Falling back to next data source...")
                    continue

        # 所有数据源都失败
        raise RuntimeError(
            f"All data sources failed for market {market}. "
            f"Last error: {last_error}"
        )

    async def check_all_sources_health(self) -> dict[str, dict[str, Any]]:
        """
        检查所有数据源的健康状态

        Returns:
            数据源健康状态字典
        """
        health_report = {}

        for source in self.sources:
            health = await self._get_source_health(source)
            health_report[source.source_name] = health

        return health_report

    async def _get_source_health(self, source: DataSourceAdapter) -> dict[str, Any]:
        """
        获取数据源健康状态（带缓存）

        Args:
            source: 数据源

        Returns:
            健康状态字典
        """
        # 简单缓存：如果5分钟内检查过，使用缓存结果
        if source.source_name in self.source_health:
            cached = self.source_health[source.source_name]
            last_check = datetime.fromisoformat(cached['last_check_time'])
            if (datetime.now() - last_check).total_seconds() < 300:
                return cached

        # 执行健康检查
        health = await source.check_health()
        self.source_health[source.source_name] = health

        return health

    @classmethod
    def create_default_router(cls, tushare_token: str) -> "DataSourceRouter":
        """
        创建默认路由器（包含TuShare和AkShare）

        Args:
            tushare_token: TuShare API Token

        Returns:
            配置好的路由器实例
        """
        # 创建数据源实例
        tushare = TuShareAdapter(config={"api_token": tushare_token})
        akshare = AkShareAdapter(config={})

        # 创建路由器
        router = cls(sources=[tushare, akshare])

        logger.info(f"Created default router with sources: {[s.source_name for s in router.sources]}")

        return router

    @classmethod
    def create_us_stock_router(cls, alphavantage_api_key: str | None = None) -> "DataSourceRouter":
        """
        创建美股数据源路由器

        Args:
            alphavantage_api_key: Alpha Vantage API Key（可选）

        Returns:
            配置好的美股路由器实例
        """
        sources = []

        # Yahoo Finance 是主数据源（免费）
        try:
            yahoo = YahooFinanceAdapter(config={})
            sources.append(yahoo)
        except Exception as e:
            logger.warning(f"Failed to create Yahoo Finance adapter: {e}")

        # Alpha Vantage 是备选数据源（需要 API Key）
        if alphavantage_api_key:
            try:
                av = AlphaVantageAdapter(config={"api_key": alphavantage_api_key})
                sources.append(av)
            except Exception as e:
                logger.warning(f"Failed to create Alpha Vantage adapter: {e}")

        router = cls(sources=sources)
        logger.info(f"Created US stock router with sources: {[s.source_name for s in router.sources]}")
        return router

    @classmethod
    def create_hk_stock_router(cls) -> "DataSourceRouter":
        """
        创建港股数据源路由器

        Returns:
            配置好的港股路由器实例
        """
        sources = []

        # AkShare 是主数据源（免费，数据全面）
        try:
            akshare_hk = AkShareHKAdapter(config={})
            sources.append(akshare_hk)
        except Exception as e:
            logger.warning(f"Failed to create AkShare HK adapter: {e}")

        # Yahoo Finance 是备选数据源（免费）
        try:
            yahoo_hk = YahooHKAdapter(config={})
            sources.append(yahoo_hk)
        except Exception as e:
            logger.warning(f"Failed to create Yahoo HK adapter: {e}")

        router = cls(sources=sources)
        logger.info(f"Created HK stock router with sources: {[s.source_name for s in router.sources]}")
        return router

    @classmethod
    def create_global_router(
        cls,
        tushare_token: str | None = None,
        alphavantage_api_key: str | None = None
    ) -> "DataSourceRouter":
        """
        创建全球股票数据源路由器（支持A股、美股、港股）

        Args:
            tushare_token: TuShare API Token
            alphavantage_api_key: Alpha Vantage API Key（可选）

        Returns:
            配置好的全球数据路由器实例
        """
        sources = []

        # A股数据源
        if tushare_token:
            try:
                tushare = TuShareAdapter(config={"api_token": tushare_token})
                sources.append(tushare)
            except Exception as e:
                logger.warning(f"Failed to create TuShare adapter: {e}")

        try:
            akshare = AkShareAdapter(config={})
            sources.append(akshare)
        except Exception as e:
            logger.warning(f"Failed to create AkShare adapter: {e}")

        # 美股数据源
        try:
            yahoo_us = YahooFinanceAdapter(config={})
            sources.append(yahoo_us)
        except Exception as e:
            logger.warning(f"Failed to create Yahoo US adapter: {e}")

        if alphavantage_api_key:
            try:
                av = AlphaVantageAdapter(config={"api_key": alphavantage_api_key})
                sources.append(av)
            except Exception as e:
                logger.warning(f"Failed to create Alpha Vantage adapter: {e}")

        # 港股数据源
        try:
            akshare_hk = AkShareHKAdapter(config={})
            sources.append(akshare_hk)
        except Exception as e:
            logger.warning(f"Failed to create AkShare HK adapter: {e}")

        try:
            yahoo_hk = YahooHKAdapter(config={})
            sources.append(yahoo_hk)
        except Exception as e:
            logger.warning(f"Failed to create Yahoo HK adapter: {e}")

        router = cls(sources=sources)
        logger.info(f"Created global router with sources: {[s.source_name for s in router.sources]}")
        return router


# =============================================================================
# 全局单例
# =============================================================================

_source_router: DataSourceRouter | None = None


def get_source_router() -> DataSourceRouter:
    """
    获取全局数据源路由器单例

    Returns:
        数据源路由器实例
    """
    global _source_router
    if _source_router is None:
        # 创建默认路由器（使用 AkShare，不需要 API Key）
        akshare = AkShareAdapter(config={})
        _source_router = DataSourceRouter(sources=[akshare])
        logger.info("Created default source router with AkShare")
    return _source_router


def set_source_router(router: DataSourceRouter) -> None:
    """
    设置全局数据源路由器（用于测试或自定义配置）

    Args:
        router: 数据源路由器实例
    """
    global _source_router
    _source_router = router
