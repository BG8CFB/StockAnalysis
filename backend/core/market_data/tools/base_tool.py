"""
市场数据工具基类

为 TradingAgents 提供市场数据工具的基础框架。
支持 A 股、美股、港股的数据查询。
"""

import logging
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from enum import Enum

from core.market_data.models import MarketType
from core.market_data.repositories.stock_info import StockInfoRepository
from core.market_data.repositories.stock_quotes import StockQuoteRepository
from core.market_data.repositories.stock_financial import (
    StockFinancialRepository,
    StockFinancialIndicatorRepository,
)
from core.market_data.repositories.stock_company import StockCompanyRepository

if TYPE_CHECKING:
    from core.market_data.managers.source_router import DataSourceRouter

logger = logging.getLogger(__name__)


class DataSource(str, Enum):
    """数据源选择"""
    AUTO = "auto"  # 自动选择
    DATABASE = "database"  # 仅从数据库获取（项目信息源）
    REALTIME = "realtime"  # 使用实时数据源（用户配置）


class MarketDataToolBase(ABC):
    """
    市场数据工具基类

    提供通用的市场数据查询功能，支持双通道数据流：
    - 数据库查询（项目信息源）
    - 实时数据获取（用户配置数据源）
    """

    def __init__(
        self,
        user_id: Optional[str] = None,
        source_router: Optional["DataSourceRouter"] = None,
        data_source: DataSource = DataSource.AUTO
    ):
        """
        初始化市场数据工具

        Args:
            user_id: 用户ID（用于用户数据源配置）
            source_router: 数据源路由器
            data_source: 数据源选择策略
        """
        self.user_id = user_id
        self.source_router = source_router
        self.data_source = data_source

        # 初始化 Repository
        self.stock_info_repo = StockInfoRepository()
        self.stock_quote_repo = StockQuoteRepository()
        self.financial_repo = StockFinancialRepository()
        self.indicator_repo = StockFinancialIndicatorRepository()
        self.company_repo = StockCompanyRepository()

    @abstractmethod
    def get_market(self) -> MarketType:
        """
        获取工具支持的市场类型

        Returns:
            市场类型
        """
        pass

    async def get_stock_info(
        self,
        symbol: str,
        use_realtime: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息

        Args:
            symbol: 股票代码
            use_realtime: 是否使用实时数据源

        Returns:
            股票信息字典，未找到返回 None
        """
        try:
            # 首先从数据库查询
            stock_data = await self.stock_info_repo.get_by_symbol(symbol)

            if stock_data:
                return stock_data

            # 如果未找到且允许使用实时数据源
            if use_realtime and self.source_router:
                logger.info(f"Stock {symbol} not in database, fetching from data source")
                stocks = await self.source_router.route_to_best_source(
                    market=self.get_market(),
                    method_name="get_stock_list",
                    status="L"
                )

                for stock in stocks:
                    if stock.symbol == symbol:
                        return {
                            "symbol": stock.symbol,
                            "market": stock.market,
                            "name": stock.name,
                            "industry": stock.industry,
                            "sector": stock.sector,
                            "listing_date": stock.listing_date,
                            "exchange": stock.exchange,
                            "status": stock.status,
                            "data_source": stock.data_source,
                        }

            logger.warning(f"Stock info not found for {symbol}")
            return None

        except Exception as e:
            logger.error(f"Failed to get stock info for {symbol}: {e}")
            return None

    async def get_daily_quotes(
        self,
        symbol: str,
        days: int = 30,
        use_realtime: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取日线行情

        Args:
            symbol: 股票代码
            days: 获取最近N天的数据
            use_realtime: 是否使用实时数据源（如果数据库数据不足）

        Returns:
            行情数据列表
        """
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

            # 从数据库查询
            quotes_data = await self.stock_quote_repo.get_quotes(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )

            # 如果数据充足，直接返回
            if quotes_data and len(quotes_data) >= days:
                return quotes_data

            # 如果允许使用实时数据源
            if use_realtime and self.source_router:
                logger.info(f"Fetching realtime quotes for {symbol}")
                quotes = await self.source_router.route_to_best_source(
                    market=self.get_market(),
                    method_name="get_daily_quotes",
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )

                return [
                    {
                        "symbol": q.symbol,
                        "trade_date": q.trade_date,
                        "open": q.open,
                        "high": q.high,
                        "low": q.low,
                        "close": q.close,
                        "pre_close": q.pre_close,
                        "volume": q.volume,
                        "amount": q.amount,
                        "change": q.change,
                        "change_pct": q.change_pct,
                        "turnover_rate": q.turnover_rate,
                        "data_source": q.data_source,
                    }
                    for q in quotes
                ]

            return quotes_data if quotes_data else []

        except Exception as e:
            logger.error(f"Failed to get daily quotes for {symbol}: {e}")
            return []

    async def get_latest_quote(
        self,
        symbol: str,
        use_realtime: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        获取最新行情

        Args:
            symbol: 股票代码
            use_realtime: 是否使用实时数据源

        Returns:
            最新行情数据，未找到返回 None
        """
        try:
            # 从数据库查询
            quote_data = await self.stock_quote_repo.get_latest_quote(symbol)

            # 如果数据库有今天的数据，直接返回
            if quote_data:
                today = datetime.now().strftime("%Y%m%d")
                if quote_data.get("trade_date") == today:
                    return quote_data

            # 如果允许使用实时数据源
            if use_realtime and self.source_router:
                logger.info(f"Fetching realtime quote for {symbol}")
                quotes = await self.source_router.route_to_best_source(
                    market=self.get_market(),
                    method_name="get_daily_quotes",
                    symbol=symbol,
                    start_date=datetime.now().strftime("%Y%m%d"),
                    end_date=datetime.now().strftime("%Y%m%d")
                )

                if quotes:
                    q = quotes[0]
                    return {
                        "symbol": q.symbol,
                        "trade_date": q.trade_date,
                        "open": q.open,
                        "high": q.high,
                        "low": q.low,
                        "close": q.close,
                        "pre_close": q.pre_close,
                        "volume": q.volume,
                        "amount": q.amount,
                        "change": q.change,
                        "change_pct": q.change_pct,
                        "turnover_rate": q.turnover_rate,
                        "data_source": q.data_source,
                    }

            return quote_data if quote_data else None

        except Exception as e:
            logger.error(f"Failed to get latest quote for {symbol}: {e}")
            return None

    async def get_financials(
        self,
        symbol: str,
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        """
        获取财务报表

        Args:
            symbol: 股票代码
            limit: 返回数量

        Returns:
            财务报表数据列表
        """
        try:
            financials_data = await self.financial_repo.get_financials(
                symbol=symbol,
                limit=limit
            )
            return financials_data if financials_data else []

        except Exception as e:
            logger.error(f"Failed to get financials for {symbol}: {e}")
            return []

    async def get_financial_indicators(
        self,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取最新财务指标

        Args:
            symbol: 股票代码

        Returns:
            财务指标数据，未找到返回 None
        """
        try:
            indicator_data = await self.indicator_repo.get_latest_indicator(symbol)
            return indicator_data

        except Exception as e:
            logger.error(f"Failed to get financial indicators for {symbol}: {e}")
            return None

    async def get_company_info(
        self,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取公司信息

        Args:
            symbol: 股票代码

        Returns:
            公司信息数据，未找到返回 None
        """
        try:
            company_data = await self.company_repo.get_by_symbol(symbol)
            return company_data

        except Exception as e:
            logger.error(f"Failed to get company info for {symbol}: {e}")
            return None

    async def search_stocks(
        self,
        keyword: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        搜索股票

        Args:
            keyword: 搜索关键词（股票代码或名称）
            limit: 返回数量

        Returns:
            股票信息列表
        """
        try:
            stocks = await self.stock_info_repo.search(
                keyword=keyword,
                market=self.get_market(),
                limit=limit
            )
            return stocks if stocks else []

        except Exception as e:
            logger.error(f"Failed to search stocks for {keyword}: {e}")
            return []

    async def get_stock_list(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取股票列表

        Args:
            limit: 返回数量

        Returns:
            股票信息列表
        """
        try:
            stocks = await self.stock_info_repo.get_by_market(
                market=self.get_market(),
                limit=limit
            )
            return stocks if stocks else []

        except Exception as e:
            logger.error(f"Failed to get stock list: {e}")
            return []
