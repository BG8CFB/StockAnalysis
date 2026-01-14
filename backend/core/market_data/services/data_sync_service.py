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

        self._adapters: Dict[str, Any] = {}
        self._router: Optional[DataSourceRouter] = None
        self._router_market: Optional[str] = None

    def _get_adapter(self, source_id: str, config: Dict[str, Any]) -> Any:
        """
        获取数据源适配器实例

        Args:
            source_id: 数据源ID
            config: 配置信息

        Returns:
            适配器实例
        """
        if source_id not in self._adapters:
            if source_id == "tushare":
                self._adapters[source_id] = TuShareAdapter(config)
            elif source_id == "akshare":
                self._adapters[source_id] = AkShareAdapter(config)
            else:
                raise ValueError(f"Unsupported data source: {source_id}")

        return self._adapters[source_id]

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
        sources = await self.system_source_repo.get_all_enabled(market)
        adapters = []

        for source_config in sources:
            try:
                adapter = self._get_adapter(source_config["source_id"], source_config["config"])
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
                market_type = MarketType(market.lower()) if market else MarketType.A_STOCK
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
            adapter = self._get_adapter(source_id, config["config"])
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
        更新数据源状态

        Args:
            market: 市场类型
            data_type: 数据类型
            source_id: 数据源ID
            status: 新状态
            response_time_ms: 响应时间
            error: 错误信息
            check_type: 检查类型
        """
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

        if status != DataSourceStatus.HEALTHY and error:
            history = DataSourceStatusHistory(
                market=market,
                data_type=data_type,
                source_type=DataSourceType.SYSTEM,
                source_id=source_id,
                event_type="api_failed",
                to_status=status.value,
                error_code=error.get("code"),
                error_message=error.get("message"),
                response_time_ms=response_time_ms,
                check_type=check_type
            )
            await self.status_history_repo.record_event(history)

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
            config = await self.system_source_repo.get_config(source_id, market.value)
            if not config:
                raise ValueError(f"Config not found for {source_id}")

            adapter = self._get_adapter(source_id, config["config"])

            logger.info(f"Syncing stock list from {source_id}")
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
        source_id: str = "tushare",
        adjust_type: Optional[str] = None,
        rollback_on_error: bool = False
    ) -> Dict[str, Any]:
        """
        同步日线行情

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            source_id: 数据源ID
            adjust_type: 复权类型
            rollback_on_error: 出错时是否回滚已写入的数据

        Returns:
            同步结果
        """
        start_time = datetime.now()
        result = {
            "task_type": "sync_daily_quotes",
            "status": "running",
            "symbol": None,
            "market": "A_STOCK",
            "data_types": ["daily_quotes"],
            "result": {}
        }

        total_upserted = 0
        failed_symbols = []
        successful_symbols = []
        rollback_candidates = []  # 记录已写入的符号，用于回滚

        try:
            config = await self.system_source_repo.get_config(source_id, "A_STOCK")
            if not config:
                raise ValueError(f"Config not found for {source_id}")

            adapter = self._get_adapter(source_id, config["config"])

            for idx, symbol in enumerate(symbols):
                try:
                    logger.info(f"Syncing daily quotes for {symbol} ({idx+1}/{len(symbols)})")
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

                except Exception as e:
                    logger.warning(f"Failed to sync {symbol}: {e}")
                    failed_symbols.append({"symbol": symbol, "error": str(e)})

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
                        raise

            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if failed_symbols:
                status = DataSourceStatus.DEGRADED
            else:
                status = DataSourceStatus.HEALTHY

            await self._update_source_status(
                market="A_STOCK",
                data_type="daily_quotes",
                source_id=source_id,
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
                "source": source_id,
                "rollback_performed": False
            }

            logger.info(f"Synced {total_upserted} quotes for {len(symbols)} symbols")

        except Exception as e:
            logger.error(f"Failed to sync daily quotes: {e}")
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            await self._update_source_status(
                market="A_STOCK",
                data_type="daily_quotes",
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
            config = await self.system_source_repo.get_config(source_id, "A_STOCK")
            if not config:
                raise ValueError(f"Config not found for {source_id}")

            adapter = self._get_adapter(source_id, config["config"])

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
            config = await self.system_source_repo.get_config(source_id, "A_STOCK")
            if not config:
                raise ValueError(f"Config not found for {source_id}")

            adapter = self._get_adapter(source_id, config["config"])

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
            if financials_failed_symbols:
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

            # 2. 财务指标数据状态
            if indicators_failed_symbols:
                indicators_status = DataSourceStatus.DEGRADED
            else:
                indicators_status = DataSourceStatus.HEALTHY

            await self._update_source_status(
                market="A_STOCK",
                data_type="financial_indicator",
                source_id=source_id,
                status=indicators_status,
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

            await self._update_source_status(
                market="A_STOCK",
                data_type="financial_indicator",
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
            config = await self.system_source_repo.get_config(source_id, "A_STOCK")
            if not config:
                raise ValueError(f"Config not found for {source_id}")

            adapter = self._get_adapter(source_id, config["config"])

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
            config = await self.system_source_repo.get_config(source_id, "A_STOCK")
            if not config:
                raise ValueError(f"Config not found for {source_id}")

            adapter = self._get_adapter(source_id, config["config"])

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
