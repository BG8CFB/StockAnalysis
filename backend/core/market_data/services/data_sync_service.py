"""
数据同步服务

负责从数据源获取数据并存储到数据库，支持多种数据类型的同步。
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio

from core.market_data.models import (
    MarketType,
    StockInfo,
    StockQuote,
    StockKLine,
    StockFinancial,
    StockFinancialIndicator,
    StockCompany,
    MacroEconomic,
)
from core.market_data.models.sync_task import DataSyncTask
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

logger = logging.getLogger(__name__)


class DataSyncService:
    """数据同步服务"""

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
        adjust_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步日线行情

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            source_id: 数据源ID
            adjust_type: 复权类型

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
                        data = quote.model_dump()
                        await self.stock_quotes_repo.upsert_quote(symbol, data)
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
                data_type="daily_quotes",
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
                "total_quotes": total_upserted,
                "failed_symbols": failed_symbols[:10],
                "source": source_id
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
                        data = kline.model_dump()
                        await self.stock_quotes_repo.upsert_quote(symbol, data)
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
            "data_types": ["financials"],
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
                    logger.info(f"Syncing financials for {symbol} ({idx+1}/{len(symbols)})")
                    financials = await adapter.get_stock_financials(
                        symbol=symbol,
                        report_date=report_date
                    )

                    upserted = 0
                    for financial in financials:
                        await self.stock_financial_repo.upsert_financial(financial)
                        upserted += 1

                    total_upserted += upserted

                    indicators = await adapter.get_financial_indicators(
                        symbol=symbol,
                        report_date=report_date
                    )

                    for indicator in indicators:
                        await self.stock_indicator_repo.upsert_indicator(indicator)
                        upserted += 1

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
                data_type="financials",
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

            logger.info(f"Synced {total_upserted} financial records for {len(symbols)} symbols")

        except Exception as e:
            logger.error(f"Failed to sync financials: {e}")
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

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
