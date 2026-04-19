"""
数据源路由器

实现数据源选择、降级策略和健康检查
"""

import inspect
import logging
from datetime import datetime
from typing import Any

from core.config import DATA_SOURCE_MAX_FAILURES
from core.market_data.models import MarketType
from core.market_data.models.api_monitor import ApiMonitor
from core.market_data.sources.a_stock import AkShareAdapter, TuShareAdapter
from core.market_data.sources.base import DataSourceAdapter
from core.market_data.sources.hk_stock import AkShareHKAdapter, YahooHKAdapter
from core.market_data.sources.us_stock import AlphaVantageAdapter, YahooFinanceAdapter

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
        self.source_health: dict[str, dict[str, Any]] = {}  # 数据源健康状态缓存
        # 简单内存缓存 API Monitor 状态 (实际应从DB加载)
        self.api_monitors: dict[str, ApiMonitor] = {}

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
        self, market: MarketType, check_health: bool = True
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
                logger.warning(
                    f"Data source {source.source_name} is disabled due to repeated failures"
                )
                continue

            # 检查健康状态
            if check_health:
                health = await self._get_source_health(source)
                if not health["is_available"]:
                    logger.warning(f"Data source {source.source_name} is not available")
                    continue

            available.append(source)

        return available

    async def get_source_for_data_type(
        self, data_type: str, market: MarketType
    ) -> DataSourceAdapter | None:
        """
        根据数据类型获取最佳数据源 (Failover Logic)

        Args:
            data_type: 数据类型 (e.g. 'minute_data', 'daily_data')
            market: 市场类型

        Returns:
            DataSourceAdapter or None
        """
        # 1. 获取该类型的 Monitor 状态
        monitor = self.api_monitors.get(data_type)

        # 默认首选 TU (如果存在)
        primary_source_name = monitor.primary_source if monitor else "TU"
        backup_source_name = monitor.backup_source if monitor else "AK"
        use_backup = monitor.is_using_backup if monitor else False

        target_source_name = backup_source_name if use_backup else primary_source_name

        # 2. 查找对应的数据源实例
        target_source = next((s for s in self.sources if s.source_name == target_source_name), None)

        # 如果目标源不可用或不支持该市场，尝试降级到另一个
        if not target_source or not target_source.supports_market(market):
            fallback_name = primary_source_name if use_backup else backup_source_name
            target_source = next((s for s in self.sources if s.source_name == fallback_name), None)

        return target_source

    async def record_failure(self, data_type: str, source_name: str) -> None:
        """记录调用失败，触发切换逻辑"""
        if data_type not in self.api_monitors:
            self.api_monitors[data_type] = ApiMonitor(
                data_type=data_type, primary_source="TU", backup_source="AK"  # 默认
            )

        monitor = self.api_monitors[data_type]
        if monitor.primary_source == source_name:
            monitor.fail_count += 1
            if monitor.fail_count >= 3:  # 阈值
                monitor.is_using_backup = True
                logger.warning(
                    f"Data type {data_type} failover to backup source {monitor.backup_source}"
                )

        monitor.last_check_time = datetime.now()
        # TODO: Save to DB

    async def record_success(self, data_type: str, source_name: str) -> None:
        """记录调用成功"""
        if data_type in self.api_monitors:
            monitor = self.api_monitors[data_type]
            if monitor.is_using_backup and source_name == monitor.primary_source:
                # 如果主源成功了（可能是探测），切回主源
                monitor.is_using_backup = False
                monitor.fail_count = 0
                logger.info(
                    f"Data type {data_type} recovered to primary source {monitor.primary_source}"
                )
            elif source_name == monitor.primary_source:
                monitor.fail_count = 0

            monitor.last_check_time = datetime.now()
            # TODO: Save to DB

    async def route_to_best_source(
        self, market: MarketType, method_name: str, *args: Any, **kwargs: Any
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
                    needs_market = bool(params and params[0] == "market")
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
                    logger.info("Falling back to next data source...")
                    continue

        # 所有数据源都失败
        raise RuntimeError(
            f"All data sources failed for market {market}. " f"Last error: {last_error}"
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
            last_check = datetime.fromisoformat(cached["last_check_time"])
            if (datetime.now() - last_check).total_seconds() < 300:
                return cached

        # 执行健康检查
        health = await source.check_health()
        self.source_health[source.source_name] = dict(health)

        return dict(health)

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

        logger.info(
            f"Created default router with sources: {[s.source_name for s in router.sources]}"
        )

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
        sources: list[DataSourceAdapter] = []

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
        logger.info(
            f"Created US stock router with sources: {[s.source_name for s in router.sources]}"
        )
        return router

    @classmethod
    def create_hk_stock_router(cls) -> "DataSourceRouter":
        """
        创建港股数据源路由器

        Returns:
            配置好的港股路由器实例
        """
        sources: list[DataSourceAdapter] = []

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
        logger.info(
            f"Created HK stock router with sources: {[s.source_name for s in router.sources]}"
        )
        return router

    @classmethod
    def create_global_router(
        cls, tushare_token: str | None = None, alphavantage_api_key: str | None = None
    ) -> "DataSourceRouter":
        """
        创建全球股票数据源路由器（支持A股、美股、港股）

        Args:
            tushare_token: TuShare API Token
            alphavantage_api_key: Alpha Vantage API Key（可选）

        Returns:
            配置好的全球数据路由器实例
        """
        sources: list[DataSourceAdapter] = []

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
        logger.info(
            f"Created global router with sources: {[s.source_name for s in router.sources]}"
        )
        return router


# =============================================================================
# 全局单例
# =============================================================================

_source_router: DataSourceRouter | None = None


def get_source_router() -> DataSourceRouter:
    """
    获取全局数据源路由器单例

    默认创建支持多市场（A股、美股、港股）的路由器。
    如果需要自定义配置，可使用 set_source_router() 覆盖。

    Returns:
        数据源路由器实例
    """
    global _source_router
    if _source_router is None:
        from core.config import TUSHARE_TOKEN

        # 创建多市场支持的路由器
        sources: list[DataSourceAdapter] = []

        # A股数据源
        try:
            akshare = AkShareAdapter(config={})
            sources.append(akshare)
        except Exception as e:
            logger.warning(f"Failed to create AkShare adapter: {e}")

        if TUSHARE_TOKEN:
            try:
                tushare = TuShareAdapter(config={"api_token": TUSHARE_TOKEN})
                sources.append(tushare)
            except Exception as e:
                logger.warning(f"Failed to create TuShare adapter: {e}")

        # 美股数据源
        try:
            yahoo_us = YahooFinanceAdapter(config={})
            sources.append(yahoo_us)
        except Exception as e:
            logger.warning(f"Failed to create Yahoo Finance adapter: {e}")

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

        _source_router = DataSourceRouter(sources=sources)
        logger.info(f"Created source router with adapters: {[s.source_name for s in sources]}")

    return _source_router


def set_source_router(router: DataSourceRouter) -> None:
    """
    设置全局数据源路由器（用于测试或自定义配置）

    Args:
        router: 数据源路由器实例
    """
    global _source_router
    _source_router = router
