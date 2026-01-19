"""
数据同步服务

负责从数据源获取数据并存储到数据库，支持多种数据类型的同步。
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from core.market_data.models import (
    MarketType,
    MacroEconomic,
)
from core.market_data.models.datasource import (
    DataSourceType,
    DataSourceStatus,
    DataSourceStatusHistory,
)
from core.market_data.repositories.datasource import (
    SystemDataSourceRepository,
    DataSourceStatusRepository,
    DataSourceStatusHistoryRepository,
)
from core.market_data.repositories.stock_info import StockInfoRepository
from core.market_data.repositories.stock_quotes import StockQuoteRepository
from core.market_data.repositories.stock_financial import (
    StockFinancialRepository,
    StockFinancialIndicatorRepository,
)
from core.market_data.repositories.stock_company import StockCompanyRepository
from core.market_data.repositories.macro_economic import MacroEconomicRepository
from core.market_data.repositories.market_news import MarketNewsRepository
from core.market_data.sources.a_stock.tushare_adapter import TuShareAdapter
from core.market_data.sources.a_stock.akshare_adapter import AkShareAdapter
from core.market_data.managers.source_router import DataSourceRouter

logger = logging.getLogger(__name__)


class DataSyncService:
    """数据同步服务（支持自动数据源切换）"""

    def __init__(self):
        self.system_source_repo = SystemDataSourceRepository()
        self.status_repo = DataSourceStatusRepository()
        self.status_history_repo = DataSourceStatusHistoryRepository()
        self.stock_info_repo = StockInfoRepository()
        self.stock_quotes_repo = StockQuoteRepository()
        self.stock_financial_repo = StockFinancialRepository()
        self.stock_indicator_repo = StockFinancialIndicatorRepository()
        self.stock_company_repo = StockCompanyRepository()
        self.macro_economic_repo = MacroEconomicRepository()
        self.market_news_repo = MarketNewsRepository()

        self._adapters: Dict[str, Any] = {}
        self._router: Optional[DataSourceRouter] = None
        self._router_market: Optional[str] = None

        # 监控服务实例（延迟加载）
        self._monitor_service = None

    def _get_monitor_service(self):
        """获取监控服务实例（延迟加载）"""
        if self._monitor_service is None:
            from core.market_data.services.source_monitor_service import SourceMonitorService
            self._monitor_service = SourceMonitorService()
        return self._monitor_service

    def _get_adapter(self, source_id: str, config: Dict[str, Any], market: str = "A_STOCK") -> Any:
        """
        获取数据源适配器实例（支持默认配置和多市场）

        Args:
            source_id: 数据源ID
            config: 配置信息（可为空，使用默认配置）
            market: 市场类型 (A_STOCK, US_STOCK, HK_STOCK)

        Returns:
            适配器实例
        """
        # 使用 source_id 和 market 组合作为缓存 key
        cache_key = f"{market}:{source_id}"

        if cache_key not in self._adapters:
            adapter_config = config if config else {}

            # A股数据源
            if market == "A_STOCK":
                if source_id == "tushare":
                    try:
                        self._adapters[cache_key] = TuShareAdapter(adapter_config)
                        logger.info(f"Created TuShare adapter (has_token: {bool(adapter_config.get('api_token'))})")
                    except ValueError as e:
                        logger.warning(f"TuShare adapter creation failed: {e}, creating with empty config")
                        self._adapters[cache_key] = TuShareAdapter({})
                elif source_id == "akshare":
                    self._adapters[cache_key] = AkShareAdapter(adapter_config)
                    logger.info("Created AkShare adapter for A_STOCK")
                else:
                    raise ValueError(f"Unsupported data source: {source_id} for market: {market}")

            # 美股数据源
            elif market == "US_STOCK":
                if source_id == "yahoo":
                    from core.market_data.sources.us_stock.yahoo_adapter import YahooFinanceAdapter
                    self._adapters[cache_key] = YahooFinanceAdapter(adapter_config)
                    logger.info("Created YahooFinance adapter for US_STOCK")
                elif source_id == "alpha_vantage":
                    from core.market_data.sources.us_stock.alphavantage_adapter import AlphaVantageAdapter
                    self._adapters[cache_key] = AlphaVantageAdapter(adapter_config)
                    logger.info("Created AlphaVantage adapter for US_STOCK")
                elif source_id == "akshare":
                    # TODO: AkShare US adapter 尚未实现，已定义但未开发
                    raise NotImplementedError(
                        f"AkShare adapter for US_STOCK is not yet implemented. "
                        f"Please use 'yahoo' or 'alpha_vantage' for US market data."
                    )
                else:
                    raise ValueError(f"Unsupported data source: {source_id} for market: {market}")

            # 港股数据源
            elif market == "HK_STOCK":
                if source_id == "yahoo":
                    from core.market_data.sources.hk_stock.yahoo_adapter import YahooHKAdapter
                    self._adapters[cache_key] = YahooHKAdapter(adapter_config)
                    logger.info("Created YahooHK adapter for HK_STOCK")
                elif source_id == "akshare":
                    from core.market_data.sources.hk_stock.akshare_adapter import AkShareHKAdapter
                    self._adapters[cache_key] = AkShareHKAdapter(adapter_config)
                    logger.info("Created AkShareHK adapter for HK_STOCK")
                else:
                    raise ValueError(f"Unsupported data source: {source_id} for market: {market}")

            else:
                raise ValueError(f"Unsupported market: {market}")

        return self._adapters[cache_key]

    async def _get_router(self, market: str = "A_STOCK") -> DataSourceRouter:
        """
        获取或创建数据源路由器（支持自动切换）

        Args:
            market: 市场类型

        Returns:
            数据源路由器
        """
        # 如果路由器已存在且市场类型相同，直接返回
        if self._router is not None and self._router_market == market:
            return self._router

        # 获取所有启用的数据源配置
        sources = await self.system_source_repo.get_enabled_configs(market, enabled_only=True)
        adapters = []

        for source_config in sources:
            try:
                adapter = self._get_adapter(source_config["source_id"], source_config["config"], market)
                # 设置优先级（从配置中读取或使用默认值）
                if "priority" in source_config:
                    adapter.set_priority(source_config["priority"])
                adapters.append(adapter)
            except Exception as e:
                logger.warning(f"Failed to create adapter for {source_config['source_id']}: {e}")

        # 创建路由器
        self._router = DataSourceRouter(sources=adapters)
        self._router_market = market
        logger.info(f"Created data source router for {market} with {len(adapters)} sources")

        return self._router

    async def _get_data_with_fallback(
        self,
        market: str,
        method_name: str,
        use_fallback: bool = True,
        *args,
        **kwargs
    ) -> Any:
        """
        使用自动降级获取数据

        Args:
            market: 市场类型
            method_name: 调用的方法名
            use_fallback: 是否使用自动降级
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            方法调用结果
        """
        if use_fallback:
            try:
                router = await self._get_router(market)
                market_type = MarketType(market.upper()) if market else MarketType.A_STOCK
                return await router.route_to_best_source(market_type, method_name, *args, **kwargs)
            except Exception as e:
                logger.error(f"All data sources failed for {method_name}: {e}")
                raise
        else:
            # 不使用自动降级，直接使用指定的 source_id
            source_id = kwargs.pop("source_id", "tushare")
            config = await self.system_source_repo.get_config(source_id, market)
            if not config:
                raise ValueError(f"Config not found for {source_id}")
            adapter = self._get_adapter(source_id, config["config"], market)
            method = getattr(adapter, method_name)
            return await method(*args, **kwargs)

    async def _update_source_status(
        self,
        market: str,
        data_type: str,
        source_id: str,
        status: DataSourceStatus,
        response_time_ms: Optional[int] = None,
        error: Optional[Dict[str, Any]] = None,
        check_type: str = "sync_task"
    ):
        """
        更新数据源状态（使用失败计数机制）

        Args:
            market: 市场类型
            data_type: 数据类型
            source_id: 数据源ID
            status: 新状态
            response_time_ms: 响应时间
            error: 错误信息
            check_type: 检查类型
        """
        monitor_service = self._get_monitor_service()

        if status == DataSourceStatus.HEALTHY:
            # 成功时重置失败计数并更新状态
            await monitor_service.handle_recovery(
                market=market,
                data_type=data_type,
                source_id=source_id,
                response_time_ms=response_time_ms or 0
            )
        elif error:
            # 失败时使用失败计数机制
            result = await monitor_service.handle_failure(
                market=market,
                data_type=data_type,
                source_id=source_id,
                error=error,
                check_type=check_type
            )
            logger.info(f"Handled failure for {source_id}/{data_type}: {result}")
        else:
            # 其他状态直接更新
            await self.status_repo.update_status(
                market=market,
                data_type=data_type,
                source_type=DataSourceType.SYSTEM,
                source_id=source_id,
                status=status,
                response_time_ms=response_time_ms,
                error=error,
                check_type=check_type
            )

    async def sync_stock_list(
        self,
        market: MarketType = MarketType.A_STOCK,
        source_id: str = "tushare",
        status: str = "L"
    ) -> Dict[str, Any]:
        """
        同步股票列表

        Args:
            market: 市场类型
            source_id: 数据源ID
            status: 上市状态

        Returns:
            同步结果
        """
        start_time = datetime.now()
        result = {
            "task_type": "sync_stock_list",
            "status": "running",
            "symbol": None,
            "market": market.value,
            "data_types": ["stock_list"],
            "result": {}
        }

        try:
            # 尝试获取配置，如果不存在使用空配置
            config = await self.system_source_repo.get_config(source_id, market.value)
            adapter_config = config["config"] if config else {}

            adapter = self._get_adapter(source_id, adapter_config, market.value)

            logger.info(f"Syncing stock list from {source_id} (config: {'found' if config else 'default'})")
            stock_list = await adapter.get_stock_list(market, status)

            upserted = 0
            for stock_info in stock_list:
                await self.stock_info_repo.upsert_stock_info(stock_info)
                upserted += 1

            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            await self._update_source_status(
                market=market.value,
                data_type="stock_list",
                source_id=source_id,
                status=DataSourceStatus.HEALTHY,
                response_time_ms=response_time_ms
            )

            result["status"] = "completed"
            result["progress"] = 100
            result["result"] = {
                "total": len(stock_list),
                "upserted": upserted,
                "source": source_id
            }

            logger.info(f"Synced {upserted} stocks from {source_id}")

        except Exception as e:
            logger.error(f"Failed to sync stock list: {e}")
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            await self._update_source_status(
                market=market.value,
                data_type="stock_list",
                source_id=source_id,
                status=DataSourceStatus.UNAVAILABLE,
                response_time_ms=response_time_ms,
                error={"code": "SYNC_ERROR", "message": str(e)}
            )

            result["status"] = "failed"
            result["error_message"] = str(e)

        return result

    async def sync_daily_quotes(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        source_id: Optional[str] = None,
        adjust_type: Optional[str] = None,
        rollback_on_error: bool = False,
        market: str = "A_STOCK"
    ) -> Dict[str, Any]:
        """
        同步日线行情（支持自动降级）

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            source_id: 数据源ID（可选，None表示自动选择）
            adjust_type: 复权类型
            rollback_on_error: 出错时是否回滚已写入的数据
            market: 市场类型 (A_STOCK, US_STOCK, HK_STOCK)

        Returns:
            同步结果
        """
        start_time = datetime.now()
        result = {
            "task_type": "sync_daily_quotes",
            "status": "running",
            "symbol": None,
            "market": market,
            "data_types": ["daily_quotes"],
            "result": {}
        }

        total_upserted = 0
        failed_symbols = []
        successful_symbols = []
        rollback_candidates = []  # 记录已写入的符号，用于回滚
        used_source_id = source_id

        try:
            # 获取可用数据源列表
            adapters = []
            if source_id:
                config = await self.system_source_repo.get_config(source_id, market)
                adapter_config = config["config"] if config else {}
                adapters.append(self._get_adapter(source_id, adapter_config, market))
            else:
                router = await self._get_router(market)
                market_enum = MarketType(market.upper()) if market else MarketType.A_STOCK
                adapters = await router.get_available_sources(market_enum)
                if not adapters:
                    raise RuntimeError(f"No available data sources for {market}")

            logger.info(f"Syncing daily quotes using {len(adapters)} sources")

            for idx, symbol in enumerate(symbols):
                symbol_success = False
                last_error = None
                
                # 对每个 symbol 尝试所有可用源
                for adapter in adapters:
                    try:
                        logger.info(f"Syncing daily quotes for {symbol} from {adapter.source_name} ({idx+1}/{len(symbols)})")
                        quotes = await adapter.get_daily_quotes(
                            symbol=symbol,
                            start_date=start_date,
                            end_date=end_date,
                            adjust_type=adjust_type
                        )

                        upserted = 0
                        for quote in quotes:
                            await self.stock_quotes_repo.upsert_quote(quote)
                            upserted += 1

                        total_upserted += upserted
                        successful_symbols.append(symbol)
                        rollback_candidates.append(symbol)
                        symbol_success = True
                        used_source_id = adapter.source_name # 记录最后一次成功的源
                        break # 成功则跳出源循环，处理下一个 symbol

                    except Exception as e:
                        last_error = e
                        logger.warning(f"Failed to sync {symbol} from {adapter.source_name}: {e}")
                        continue # 尝试下一个源
                
                if not symbol_success:
                    failed_symbols.append({"symbol": symbol, "error": str(last_error)})
                    # 如果配置了出错回滚，立即回滚已写入的数据
                    if rollback_on_error and rollback_candidates:
                        count = len(rollback_candidates)
                        logger.warning(
                            f"Rolling back {count} symbols due to error"
                        )
                        await self._rollback_daily_quotes(
                            rollback_candidates, start_date, end_date
                        )
                        rollback_candidates.clear()
                        raise last_error

            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if failed_symbols:
                status = DataSourceStatus.DEGRADED
            else:
                status = DataSourceStatus.HEALTHY

            # 更新状态（仅当有明确的源ID时，或者我们可以记录 primary source）
            # 这里简化处理：如果是自动路由，我们可能无法准确归因于单一源的状态。
            # 但为了监控，我们可以记录最后使用的源，或者不记录。
            if used_source_id:
                await self._update_source_status(
                    market=market,
                    data_type="daily_quote",
                    source_id=used_source_id,
                    status=status,
                    response_time_ms=response_time_ms
                )

            result["status"] = "completed" if not failed_symbols else "completed_with_errors"
            result["progress"] = 100
            result["result"] = {
                "total_symbols": len(symbols),
                "successful": len(successful_symbols),
                "successful_symbols": successful_symbols,
                "failed": len(failed_symbols),
                "failed_symbols": failed_symbols[:10],
                "total_quotes": total_upserted,
                "source": used_source_id or "multiple",
                "rollback_performed": False
            }

            logger.info(f"Synced {total_upserted} quotes for {len(symbols)} symbols")

        except Exception as e:
            logger.error(f"Failed to sync daily quotes: {e}")
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if source_id:
                await self._update_source_status(
                    market=market,
                    data_type="daily_quote",
                    source_id=source_id,
                    status=DataSourceStatus.UNAVAILABLE,
                    response_time_ms=response_time_ms,
                    error={"code": "SYNC_ERROR", "message": str(e)}
                )

            result["status"] = "failed"
            result["error_message"] = str(e)

        return result

    async def sync_minute_quotes(
        self,
        symbols: List[str],
        trade_date: str,
        source_id: str = "akshare",
        freq: str = "1min"
    ) -> Dict[str, Any]:
        """
        同步分钟K线数据

        Args:
            symbols: 股票代码列表
            trade_date: 交易日期
            source_id: 数据源ID
            freq: 频率

        Returns:
            同步结果
        """
        start_time = datetime.now()
        result = {
            "task_type": "sync_minute_quotes",
            "status": "running",
            "symbol": None,
            "market": "A_STOCK",
            "data_types": ["minute_quotes"],
            "result": {}
        }

        total_upserted = 0
        failed_symbols = []

        try:
            # 尝试获取配置，如果不存在使用空配置
            config = await self.system_source_repo.get_config(source_id, "A_STOCK")
            adapter_config = config["config"] if config else {}

            adapter = self._get_adapter(source_id, adapter_config, "A_STOCK")

            logger.info(f"Syncing daily quotes from {source_id} (config: {'found' if config else 'default'})")

            for idx, symbol in enumerate(symbols):
                try:
                    logger.info(f"Syncing minute quotes for {symbol} ({idx+1}/{len(symbols)})")
                    klines = await adapter.get_minute_quotes(
                        symbol=symbol,
                        trade_date=trade_date,
                        freq=freq
                    )

                    upserted = 0
                    for kline in klines:
                        await self.stock_quotes_repo.upsert_quote(kline)
                        upserted += 1

                    total_upserted += upserted

                except Exception as e:
                    logger.warning(f"Failed to sync {symbol}: {e}")
                    failed_symbols.append({"symbol": symbol, "error": str(e)})

            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if failed_symbols:
                status = DataSourceStatus.DEGRADED
            else:
                status = DataSourceStatus.HEALTHY

            await self._update_source_status(
                market="A_STOCK",
                data_type="minute_quotes",
                source_id=source_id,
                status=status,
                response_time_ms=response_time_ms
            )

            result["status"] = "completed" if not failed_symbols else "completed_with_errors"
            result["progress"] = 100
            result["result"] = {
                "total_symbols": len(symbols),
                "successful": len(symbols) - len(failed_symbols),
                "failed": len(failed_symbols),
                "total_klines": total_upserted,
                "failed_symbols": failed_symbols[:10],
                "source": source_id
            }

            logger.info(f"Synced {total_upserted} minute klines for {len(symbols)} symbols")

        except Exception as e:
            logger.error(f"Failed to sync minute quotes: {e}")
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            await self._update_source_status(
                market="A_STOCK",
                data_type="minute_quotes",
                source_id=source_id,
                status=DataSourceStatus.UNAVAILABLE,
                response_time_ms=response_time_ms,
                error={"code": "SYNC_ERROR", "message": str(e)}
            )

            result["status"] = "failed"
            result["error_message"] = str(e)

        return result

    async def sync_financials(
        self,
        symbols: List[str],
        report_date: Optional[str] = None,
        source_id: str = "tushare"
    ) -> Dict[str, Any]:
        """
        同步财务数据

        同步两种财务数据：
        1. 财务报表数据 (financials): 利润表、资产负债表、现金流量表
        2. 财务指标数据 (financial_indicator): ROE、负债率等财务比率

        Args:
            symbols: 股票代码列表
            report_date: 报告期
            source_id: 数据源ID

        Returns:
            同步结果
        """
        start_time = datetime.now()
        result = {
            "task_type": "sync_financials",
            "status": "running",
            "symbol": None,
            "market": "A_STOCK",
            "data_types": ["financials", "financial_indicator"],
            "result": {}
        }

        # 分别统计两种数据
        financials_upserted = 0
        indicators_upserted = 0
        financials_failed_symbols = []
        indicators_failed_symbols = []

        try:
            # 尝试获取配置，如果不存在使用空配置
            config = await self.system_source_repo.get_config(source_id, "A_STOCK")
            adapter_config = config["config"] if config else {}

            adapter = self._get_adapter(source_id, adapter_config, "A_STOCK")

            logger.info(f"Syncing daily quotes from {source_id} (config: {'found' if config else 'default'})")

            for idx, symbol in enumerate(symbols):
                # 1. 同步财务报表数据
                try:
                    logger.info(f"Syncing financial statements for {symbol} ({idx+1}/{len(symbols)})")
                    financials = await adapter.get_stock_financials(
                        symbol=symbol,
                        report_date=report_date
                    )

                    for financial in financials:
                        await self.stock_financial_repo.upsert_financial(financial)
                        financials_upserted += 1

                except Exception as e:
                    logger.warning(f"Failed to sync financial statements for {symbol}: {e}")
                    financials_failed_symbols.append({"symbol": symbol, "error": str(e)})

                # 2. 同步财务指标数据
                try:
                    logger.info(f"Syncing financial indicators for {symbol} ({idx+1}/{len(symbols)})")
                    indicators = await adapter.get_financial_indicators(
                        symbol=symbol,
                        report_date=report_date
                    )

                    for indicator in indicators:
                        await self.stock_indicator_repo.upsert_indicator(indicator)
                        indicators_upserted += 1

                except Exception as e:
                    logger.warning(f"Failed to sync financial indicators for {symbol}: {e}")
                    indicators_failed_symbols.append({"symbol": symbol, "error": str(e)})

            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 分别更新两种数据的状态
            # 1. 财务报表数据状态
            if financials_failed_symbols or indicators_failed_symbols:
                financials_status = DataSourceStatus.DEGRADED
            else:
                financials_status = DataSourceStatus.HEALTHY

            await self._update_source_status(
                market="A_STOCK",
                data_type="financials",
                source_id=source_id,
                status=financials_status,
                response_time_ms=response_time_ms
            )

            # 计算整体状态
            total_failed = len(financials_failed_symbols) + len(indicators_failed_symbols)
            if total_failed == 0:
                result["status"] = "completed"
            else:
                result["status"] = "completed_with_errors"

            result["progress"] = 100
            result["result"] = {
                "total_symbols": len(symbols),
                "financials": {
                    "upserted": financials_upserted,
                    "successful": len(symbols) - len(financials_failed_symbols),
                    "failed": len(financials_failed_symbols),
                    "failed_symbols": financials_failed_symbols[:10]
                },
                "indicators": {
                    "upserted": indicators_upserted,
                    "successful": len(symbols) - len(indicators_failed_symbols),
                    "failed": len(indicators_failed_symbols),
                    "failed_symbols": indicators_failed_symbols[:10]
                },
                "total_records": financials_upserted + indicators_upserted,
                "source": source_id
            }

            logger.info(
                f"Synced financial data: {financials_upserted} statements, "
                f"{indicators_upserted} indicators for {len(symbols)} symbols"
            )

        except Exception as e:
            logger.error(f"Failed to sync financials: {e}")
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 同时标记两种数据为不可用
            await self._update_source_status(
                market="A_STOCK",
                data_type="financials",
                source_id=source_id,
                status=DataSourceStatus.UNAVAILABLE,
                response_time_ms=response_time_ms,
                error={"code": "SYNC_ERROR", "message": str(e)}
            )

            result["status"] = "failed"
            result["error_message"] = str(e)

        return result

    async def sync_company_info(
        self,
        symbols: List[str],
        source_id: str = "tushare"
    ) -> Dict[str, Any]:
        """
        同步公司信息

        Args:
            symbols: 股票代码列表
            source_id: 数据源ID

        Returns:
            同步结果
        """
        start_time = datetime.now()
        result = {
            "task_type": "sync_company_info",
            "status": "running",
            "symbol": None,
            "market": "A_STOCK",
            "data_types": ["company_info"],
            "result": {}
        }

        total_upserted = 0
        failed_symbols = []

        try:
            # 尝试获取配置，如果不存在使用空配置
            config = await self.system_source_repo.get_config(source_id, "A_STOCK")
            adapter_config = config["config"] if config else {}

            adapter = self._get_adapter(source_id, adapter_config, "A_STOCK")

            logger.info(f"Syncing daily quotes from {source_id} (config: {'found' if config else 'default'})")

            for idx, symbol in enumerate(symbols):
                try:
                    logger.info(f"Syncing company info for {symbol} ({idx+1}/{len(symbols)})")
                    company = await adapter.get_stock_company(symbol)

                    if company:
                        await self.stock_company_repo.upsert_company(company)
                        total_upserted += 1

                except Exception as e:
                    logger.warning(f"Failed to sync {symbol}: {e}")
                    failed_symbols.append({"symbol": symbol, "error": str(e)})

            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if failed_symbols:
                status = DataSourceStatus.DEGRADED
            else:
                status = DataSourceStatus.HEALTHY

            await self._update_source_status(
                market="A_STOCK",
                data_type="company_info",
                source_id=source_id,
                status=status,
                response_time_ms=response_time_ms
            )

            result["status"] = "completed" if not failed_symbols else "completed_with_errors"
            result["progress"] = 100
            result["result"] = {
                "total_symbols": len(symbols),
                "successful": len(symbols) - len(failed_symbols),
                "failed": len(failed_symbols),
                "total_records": total_upserted,
                "failed_symbols": failed_symbols[:10],
                "source": source_id
            }

            logger.info(f"Synced {total_upserted} company records for {len(symbols)} symbols")

        except Exception as e:
            logger.error(f"Failed to sync company info: {e}")
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            await self._update_source_status(
                market="A_STOCK",
                data_type="company_info",
                source_id=source_id,
                status=DataSourceStatus.UNAVAILABLE,
                response_time_ms=response_time_ms,
                error={"code": "SYNC_ERROR", "message": str(e)}
            )

            result["status"] = "failed"
            result["error_message"] = str(e)

        return result

    async def sync_company_info_with_fallback(
        self,
        symbols: List[str],
        source_id: str = "tushare"
    ) -> Dict[str, Any]:
        """
        同步公司信息（带自动降级）

        Args:
            symbols: 股票代码列表
            source_id: 首选数据源ID

        Returns:
            同步结果
        """
        start_time = datetime.now()
        result = {
            "task_type": "sync_company_info_with_fallback",
            "status": "running",
            "symbol": None,
            "market": "A_STOCK",
            "data_types": ["company_info"],
            "result": {}
        }

        # 数据源优先级列表（按优先级排序）
        sources_to_try = []
        if source_id == "tushare":
            sources_to_try = ["tushare", "akshare"]
        else:
            sources_to_try = [source_id, "akshare"]

        last_error = None
        successful_source = None

        for src_id in sources_to_try:
            try:
                logger.info(f"Trying to sync company info from {src_id}")
                # 尝试获取配置，如果不存在使用空配置
                config = await self.system_source_repo.get_config(src_id, "A_STOCK")
                adapter_config = config.get("config", {}) if config else {}

                adapter = self._get_adapter(src_id, adapter_config, "A_STOCK")
                logger.info(f"Created {src_id} adapter (config: {'found' if config else 'default'})")

                total_upserted = 0
                failed_symbols = []

                for idx, symbol in enumerate(symbols):
                    try:
                        logger.info(f"Syncing company info for {symbol} from {src_id} ({idx+1}/{len(symbols)})")
                        company = await adapter.get_stock_company(symbol)

                        if company:
                            await self.stock_company_repo.upsert_company(company)
                            total_upserted += 1

                    except Exception as e:
                        logger.warning(f"Failed to sync {symbol} from {src_id}: {e}")
                        failed_symbols.append({"symbol": symbol, "error": str(e)})

                # 成功获取数据
                successful_source = src_id
                response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                await self._update_source_status(
                    market="A_STOCK",
                    data_type="company_info",
                    source_id=src_id,
                    status=DataSourceStatus.HEALTHY,
                    response_time_ms=response_time_ms
                )

                result["status"] = "completed"
                result["progress"] = 100
                result["result"] = {
                    "total_symbols": len(symbols),
                    "successful": len(symbols) - len(failed_symbols),
                    "failed": len(failed_symbols),
                    "total_records": total_upserted,
                    "failed_symbols": failed_symbols[:10],
                    "source": src_id
                }

                logger.info(f"Successfully synced {total_upserted} company records from {src_id}")
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Failed to sync company info from {src_id}: {e}")
                # 标记该数据源状态
                try:
                    await self._update_source_status(
                        market="A_STOCK",
                        data_type="company_info",
                        source_id=src_id,
                        status=DataSourceStatus.UNAVAILABLE,
                        response_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                        error={"code": "SYNC_ERROR", "message": str(e)}
                    )
                except Exception:
                    pass
                continue

        # 所有数据源都失败
        response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        result["status"] = "failed"
        result["error_message"] = f"All data sources failed. Last error: {last_error}"
        result["result"] = {"source": "none"}

        logger.error(f"Failed to sync company info from all sources: {last_error}")
        return result

    async def sync_macro_economic(
        self,
        indicators: List[str],
        source_id: str = "tushare"
    ) -> Dict[str, Any]:
        """
        同步宏观经济数据

        Args:
            indicators: 指标列表
            source_id: 数据源ID

        Returns:
            同步结果
        """
        start_time = datetime.now()
        result = {
            "task_type": "sync_macro_economic",
            "status": "running",
            "symbol": None,
            "market": "A_STOCK",
            "data_types": ["macro_economic"],
            "result": {}
        }

        total_upserted = 0
        failed_indicators = []

        try:
            # 尝试获取配置，如果不存在使用空配置
            config = await self.system_source_repo.get_config(source_id, "A_STOCK")
            adapter_config = config["config"] if config else {}

            adapter = self._get_adapter(source_id, adapter_config, "A_STOCK")

            logger.info(f"Syncing daily quotes from {source_id} (config: {'found' if config else 'default'})")

            for indicator in indicators:
                try:
                    logger.info(f"Syncing {indicator}")

                    if indicator == "shibor":
                        data_list = await adapter.get_shibor()
                    elif indicator == "cpi":
                        data_list = await adapter.get_cpi()
                    elif indicator == "ppi":
                        data_list = await adapter.get_ppi()
                    elif indicator == "pmi_caixin":
                        data_list = await adapter.get_pmi_caixin()
                    elif indicator == "pmi_cic":
                        data_list = await adapter.get_pmi_cic()
                    elif indicator == "money_supply":
                        data_list = await adapter.get_money_supply()
                    else:
                        logger.warning(f"Unknown indicator: {indicator}")
                        continue

                    for data in data_list:
                        macro = MacroEconomic(
                            indicator=indicator,
                            period=data.get("period") or data.get("trade_date", ""),
                            value=data.get("value", 0),
                            unit=data.get("unit"),
                            yoy=data.get("yoy"),
                            mom=data.get("mom"),
                            data_source=source_id
                        )
                        await self.macro_economic_repo.upsert_macro(macro)
                        total_upserted += 1

                except Exception as e:
                    logger.warning(f"Failed to sync {indicator}: {e}")
                    failed_indicators.append({"indicator": indicator, "error": str(e)})

            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if failed_indicators:
                status = DataSourceStatus.DEGRADED
            else:
                status = DataSourceStatus.HEALTHY

            await self._update_source_status(
                market="A_STOCK",
                data_type="macro_economic",
                source_id=source_id,
                status=status,
                response_time_ms=response_time_ms
            )

            result["status"] = "completed" if not failed_indicators else "completed_with_errors"
            result["progress"] = 100
            result["result"] = {
                "total_indicators": len(indicators),
                "successful": len(indicators) - len(failed_indicators),
                "failed": len(failed_indicators),
                "total_records": total_upserted,
                "failed_indicators": failed_indicators,
                "source": source_id
            }

            logger.info(f"Synced {total_upserted} macro economic records")

        except Exception as e:
            logger.error(f"Failed to sync macro economic: {e}")
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            await self._update_source_status(
                market="A_STOCK",
                data_type="macro_economic",
                source_id=source_id,
                status=DataSourceStatus.UNAVAILABLE,
                response_time_ms=response_time_ms,
                error={"code": "SYNC_ERROR", "message": str(e)}
            )

            result["status"] = "failed"
            result["error_message"] = str(e)

        return result

    async def sync_all_for_symbol(
        self,
        symbol: str,
        source_id: str = "tushare"
    ) -> Dict[str, Any]:
        """
        同步指定股票的所有数据类型

        Args:
            symbol: 股票代码
            source_id: 数据源ID

        Returns:
            同步结果
        """
        results = {}

        results["company_info"] = await self.sync_company_info([symbol], source_id)
        results["financials"] = await self.sync_financials([symbol], source_id)

        return {
            "symbol": symbol,
            "results": results,
            "overall_status": "completed"
        }

    # ==================== 回滚方法 ====================

    async def _rollback_daily_quotes(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
    ) -> None:
        """
        回滚已写入的日线数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
        """
        for symbol in symbols:
            try:
                # 删除指定日期范围内的数据
                await self.stock_quotes_repo.delete_quotes_in_range(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                logger.info(f"Rolled back quotes for {symbol} ({start_date} to {end_date})")
            except Exception as e:
                logger.error(f"Failed to rollback quotes for {symbol}: {e}")

    # ==================== 支持自动降级的数据同步方法 ====================

    async def sync_stock_list_with_fallback(
        self,
        market: MarketType = MarketType.A_STOCK,
        status: str = "L"
    ) -> Dict[str, Any]:
        """
        同步股票列表（支持自动降级）

        依次尝试所有配置的数据源，直到成功为止。
        如果没有配置任何数据源，使用默认数据源列表（tushare -> akshare）。

        Args:
            market: 市场类型
            status: 上市状态

        Returns:
            同步结果
        """
        # 获取所有启用的数据源配置
        configs = await self.system_source_repo.get_enabled_configs(market.value)
        configs = sorted(configs, key=lambda x: x.get("priority", 999))

        # 如果没有配置任何数据源，使用默认数据源列表
        if not configs:
            logger.warning(f"No configured data sources for {market.value}, using default fallback order")
            # 创建默认配置（用于降级）
            default_configs = [
                {"source_id": "tushare", "priority": 1, "config": {}},
                {"source_id": "akshare", "priority": 2, "config": {}}
            ]
            configs = default_configs

        last_error = None
        successful_source = None

        for config in configs:
            source_id = config["source_id"]
            try:
                logger.info(f"Trying to sync stock list from {source_id} (config: {'db' if 'priority' in config else 'default'})")
                result = await self.sync_stock_list(market=market, source_id=source_id, status=status)

                if result["status"] == "completed":
                    successful_source = source_id
                    logger.info(f"Successfully synced stock list from {source_id}")
                    # 更新结果中的数据源信息
                    result["result"]["source"] = source_id
                    return result
                elif result["status"] == "failed":
                    last_error = result.get("error_message", "Unknown error")
                    logger.warning(f"Failed to sync from {source_id}: {last_error}")
                    continue

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Exception while syncing from {source_id}: {e}")
                continue

        # 所有数据源都失败
        return {
            "task_type": "sync_stock_list",
            "status": "failed",
            "market": market.value,
            "error_message": f"All data sources failed. Last error: {last_error}",
            "attempted_sources": [c["source_id"] for c in configs]
        }

    async def sync_daily_quotes_with_fallback(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        adjust_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步日线行情（支持自动降级）

        依次尝试所有配置的数据源，直到成功为止。

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            adjust_type: 复权类型

        Returns:
            同步结果
        """
        # 获取所有启用的数据源配置
        configs = await self.system_source_repo.get_enabled_configs("A_STOCK")
        configs = sorted(configs, key=lambda x: x.get("priority", 999))

        # 如果没有配置的数据源，使用默认降级顺序
        if not configs:
            logger.warning("No configured data sources for A_STOCK, using default fallback order")
            default_configs = [
                {"source_id": "tushare", "priority": 1, "config": {}},
                {"source_id": "akshare", "priority": 2, "config": {}}
            ]
            configs = default_configs

        last_error = None
        successful_source = None

        for config in configs:
            source_id = config["source_id"]
            try:
                logger.info(f"Trying to sync daily quotes from {source_id}")
                result = await self.sync_daily_quotes(
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                    source_id=source_id,
                    adjust_type=adjust_type
                )

                if result["status"] in ["completed", "completed_with_errors"]:
                    successful_source = source_id
                    logger.info(f"Successfully synced daily quotes from {source_id}")
                    return result
                elif result["status"] == "failed":
                    last_error = result.get("error_message", "Unknown error")
                    logger.warning(f"Failed to sync from {source_id}: {last_error}")
                    continue

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Exception while syncing from {source_id}: {e}")
                continue

        # 所有数据源都失败
        return {
            "task_type": "sync_daily_quotes",
            "status": "failed",
            "market": "A_STOCK",
            "error_message": f"All data sources failed. Last error: {last_error}",
            "attempted_sources": [c["source_id"] for c in configs]
        }

    async def sync_financials_with_fallback(
        self,
        symbols: List[str],
        report_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步财务数据（支持自动降级）

        依次尝试所有配置的数据源，直到成功为止。

        Args:
            symbols: 股票代码列表
            report_date: 报告期

        Returns:
            同步结果
        """
        # 获取所有启用的数据源配置
        configs = await self.system_source_repo.get_enabled_configs("A_STOCK")
        configs = sorted(configs, key=lambda x: x.get("priority", 999))

        # 如果没有配置的数据源，使用默认降级顺序
        if not configs:
            logger.warning("No configured data sources for A_STOCK, using default fallback order")
            default_configs = [
                {"source_id": "tushare", "priority": 1, "config": {}},
                {"source_id": "akshare", "priority": 2, "config": {}}
            ]
            configs = default_configs

        last_error = None
        successful_source = None

        for config in configs:
            source_id = config["source_id"]
            try:
                logger.info(f"Trying to sync financials from {source_id}")
                result = await self.sync_financials(
                    symbols=symbols,
                    report_date=report_date,
                    source_id=source_id
                )

                if result["status"] in ["completed", "completed_with_errors"]:
                    successful_source = source_id
                    logger.info(f"Successfully synced financials from {source_id}")
                    return result
                elif result["status"] == "failed":
                    last_error = result.get("error_message", "Unknown error")
                    logger.warning(f"Failed to sync from {source_id}: {last_error}")
                    continue

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Exception while syncing from {source_id}: {e}")
                continue

        # 所有数据源都失败
        return {
            "task_type": "sync_financials",
            "status": "failed",
            "market": "A_STOCK",
            "error_message": f"All data sources failed. Last error: {last_error}",
            "attempted_sources": [c["source_id"] for c in configs]
        }

    async def sync_market_news(
        self,
        source_id: str = "tushare",
        limit: int = 50,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步市场新闻
        
        Args:
            source_id: 数据源ID
            limit: 限制数量
            symbol: 个股代码（可选）
            
        Returns:
            同步结果
        """
        start_time = datetime.now()
        result = {
            "task_type": "sync_market_news",
            "status": "running",
            "symbol": symbol,
            "market": "A_STOCK",
            "data_types": ["market_news"],
            "result": {}
        }
        
        try:
            # 尝试获取配置，如果不存在使用空配置
            config = await self.system_source_repo.get_config(source_id, "A_STOCK")
            adapter_config = config["config"] if config else {}
            
            adapter = self._get_adapter(source_id, adapter_config, "A_STOCK")
            
            logger.info(f"Syncing market news from {source_id}")
            
            # 使用自动降级逻辑
            if source_id == "tushare":
                # Tushare news 需要 start_date/end_date
                from datetime import timedelta
                end_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
                
                news_list = await adapter.get_market_news(
                    start_date=start_date,
                    end_date=end_date,
                    src="sina"
                )
            else:
                # AkShare news
                news_list = await adapter.get_market_news(
                    symbol=symbol,
                    limit=limit
                )
                
            upserted = 0
            for news in news_list:
                await self.market_news_repo.upsert_news(news)
                upserted += 1
                
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            await self._update_source_status(
                market="A_STOCK",
                data_type="market_news",
                source_id=source_id,
                status=DataSourceStatus.HEALTHY,
                response_time_ms=response_time_ms
            )
            
            result["status"] = "completed"
            result["progress"] = 100
            result["result"] = {
                "total": len(news_list),
                "upserted": upserted,
                "source": source_id
            }
            
            logger.info(f"Synced {upserted} news items from {source_id}")
            
        except Exception as e:
            logger.error(f"Failed to sync market news: {e}")
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            await self._update_source_status(
                market="A_STOCK",
                data_type="market_news",
                source_id=source_id,
                status=DataSourceStatus.UNAVAILABLE,
                response_time_ms=response_time_ms,
                error={"code": "SYNC_ERROR", "message": str(e)}
            )
            
            result["status"] = "failed"
            result["error_message"] = str(e)
            
        return result
