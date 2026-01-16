"""
数据源抽象基类

定义所有数据源适配器必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime

from core.market_data.models import (
    StockInfo,
    StockQuote,
    StockFinancial,
    StockFinancialIndicator,
    MarketType,
)


class DataSourceAdapter(ABC):
    """
    数据源适配器抽象基类

    所有数据源（TuShare、AkShare等）都必须继承此类并实现所有抽象方法
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据源适配器

        Args:
            config: 数据源配置（API密钥等）
        """
        self.config = config or {}
        self.source_name = self.__class__.__name__
        self.is_available = True  # 数据源是否可用
        self.last_check_time = None  # 最后检查时间
        self.failure_count = 0  # 连续失败次数
        self._priority = 100  # 默认优先级（数字越小优先级越高）

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        测试数据源连接

        Returns:
            bool: 连接成功返回True，否则返回False
        """
        pass

    @abstractmethod
    async def get_stock_list(
        self,
        market: MarketType,
        status: str = "L"
    ) -> List[StockInfo]:
        """
        获取股票列表

        Args:
            market: 市场类型
            status: 上市状态（L上市/D退市/P暂停）

        Returns:
            股票信息列表
        """
        pass

    @abstractmethod
    async def get_daily_quotes(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust_type: Optional[str] = None
    ) -> List[StockQuote]:
        """
        获取日线行情

        Args:
            symbol: 股票代码
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            adjust_type: 复权类型（qfq前复权/hfq后复权/None不复权）

        Returns:
            日线行情列表
        """
        pass

    @abstractmethod
    async def get_stock_financials(
        self,
        symbol: str,
        report_date: Optional[str] = None,
        report_type: Optional[str] = None
    ) -> List[StockFinancial]:
        """
        获取财务报表

        Args:
            symbol: 股票代码
            report_date: 报告期（YYYYMMDD）
            report_type: 报告类型

        Returns:
            财务报表列表
        """
        pass

    @abstractmethod
    async def get_financial_indicators(
        self,
        symbol: str,
        report_date: Optional[str] = None
    ) -> List[StockFinancialIndicator]:
        """
        获取财务指标

        Args:
            symbol: 股票代码
            report_date: 报告期（YYYYMMDD）

        Returns:
            财务指标列表
        """
        pass

    @abstractmethod
    def supports_market(self, market: MarketType) -> bool:
        """
        检查数据源是否支持指定市场

        Args:
            market: 市场类型

        Returns:
            bool: 支持返回True，否则返回False
        """
        pass

    def get_priority(self) -> int:
        """
        获取数据源优先级

        Returns:
            int: 优先级（数字越小优先级越高）
        """
        return self._priority

    def set_priority(self, priority: int) -> None:
        """
        设置数据源优先级

        Args:
            priority: 优先级值（数字越小优先级越高）
        """
        if not isinstance(priority, int) or priority < 0:
            raise ValueError(f"Priority must be a non-negative integer, got {priority}")
        self._priority = priority

    async def check_health(self) -> Dict[str, Any]:
        """
        检查数据源健康状态

        Returns:
            健康状态字典，包含：
            - is_available: 是否可用
            - response_time_ms: 响应时间（毫秒）
            - last_check_time: 最后检查时间
            - failure_count: 连续失败次数
            - error: 最后一次错误信息（如果有）
        """
        start_time = datetime.now()
        error = None

        try:
            is_available = await self.test_connection()
            if is_available:
                self.failure_count = 0  # 成功后重置失败计数
        except Exception as e:
            is_available = False
            error = str(e)
            self.failure_count += 1

        end_time = datetime.now()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        self.last_check_time = end_time
        self.is_available = is_available

        return {
            "is_available": is_available,
            "response_time_ms": response_time_ms,
            "last_check_time": end_time.isoformat(),
            "failure_count": self.failure_count,
            "error": error,
        }

    def should_disable(self, max_failures: int = 3) -> bool:
        """
        判断是否应该禁用该数据源

        Args:
            max_failures: 最大允许连续失败次数

        Returns:
            bool: 超过最大失败次数返回True
        """
        return self.failure_count >= max_failures

    def reset_failure_count(self) -> None:
        """重置失败计数"""
        self.failure_count = 0

    # ==================== 监控相关方法 ====================

    async def _call_with_monitoring(
        self,
        func: Callable,
        market: str,
        data_type: str,
        *args,
        **kwargs
    ) -> Any:
        """
        执行带监控的API调用

        自动记录API调用的成功/失败状态到数据库。

        Args:
            func: 要执行的异步函数
            market: 市场类型
            data_type: 数据类型
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果

        Raises:
            Exception: 函数执行失败时抛出原始异常

        使用方式:
            result = await self._call_with_monitoring(
                self._actual_api_method,
                "A_STOCK",
                "daily_quote",
                symbol="000001.SZ",
                start_date="20240101",
                end_date="20240131"
            )
        """
        from core.market_data.services.source_call_monitor import monitor_api_context

        # 获取source_id
        source_id = self._get_source_id()

        async with monitor_api_context(market, data_type, source_id, check_type="api_call"):
            return await func(*args, **kwargs)

    def _get_source_id(self) -> str:
        """
        获取数据源ID

        Returns:
            数据源ID字符串
        """
        class_name = self.__class__.__name__.lower()

        if 'tushare' in class_name:
            return 'tushare'
        elif 'akshare' in class_name:
            return 'akshare'
        elif 'yahoo' in class_name:
            # 区分Yahoo US和Yahoo HK
            if 'hk' in class_name:
                return 'yahoo'
            return 'yahoo'
        elif 'alpha' in class_name or 'vantage' in class_name:
            return 'alpha_vantage'
        else:
            return 'unknown'
