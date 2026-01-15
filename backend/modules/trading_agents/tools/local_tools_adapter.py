"""
Local 工具适配器

将项目内部的 Market Data 工具转换为 LangChain 可用的 BaseTool 格式。

**版本**: v1.0
**最后更新**: 2026-01-15
"""

import logging
from typing import Optional, List, Dict, Any, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from core.market_data.tools.a_stock_tools import AStockTool
from core.market_data.managers.source_router import DataSourceRouter

logger = logging.getLogger(__name__)


# =============================================================================
# LangChain 工具输入模式
# =============================================================================

class GetStockQuotesInput(BaseModel):
    """获取股票行情输入参数"""
    symbol: str = Field(description="股票代码，如 600000 或 600000.SH")


class GetStockInfoInput(BaseModel):
    """获取公司信息输入参数"""
    symbol: str = Field(description="股票代码，如 600000 或 600000.SH")


class GetStockListInput(BaseModel):
    """获取股票列表输入参数"""
    limit: int = Field(default=100, description="返回数量限制")


# =============================================================================
# LangChain 工具实现
# =============================================================================

class GetStockQuotesTool(BaseTool):
    """获取股票实时行情工具"""
    name: str = "get_stock_quotes"
    description: str = "获取股票的实时行情数据，包括价格、成交量、涨跌幅等。输入股票代码（如 600000 或 000001）。"
    args_schema: Type[BaseModel] = GetStockQuotesInput

    # 使用 Pydantic Field 定义字段
    user_id: str = Field(default="")
    source_router: Any = Field(default=None)

    def __init__(self, user_id: str, source_router, **kwargs):
        super().__init__(**kwargs)
        # 使用 object.__setattr__ 绕过 Pydantic 的验证
        object.__setattr__(self, 'user_id', user_id)
        object.__setattr__(self, 'source_router', source_router)
        object.__setattr__(self, '_a_stock_tool', None)

    @property
    def a_stock_tool(self):
        if self._a_stock_tool is None:
            object.__setattr__(self, '_a_stock_tool', AStockTool(user_id=self.user_id, source_router=self.source_router))
        return self._a_stock_tool

    def _run(self, symbol: str) -> Dict[str, Any]:
        """同步执行获取行情（由 LangChain 调用）"""
        # 由于实际调用是异步的，这里需要在同步上下文中运行
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在异步上下文中，创建新循环
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.a_stock_tool.get_realtime_quote(symbol)
                    )
                    quote = future.result(timeout=30)
            else:
                quote = asyncio.run(self.a_stock_tool.get_realtime_quote(symbol))

            if quote:
                return {
                    "symbol": quote.get("symbol"),
                    "name": quote.get("name"),
                    "price": quote.get("price"),
                    "change": quote.get("change"),
                    "change_pct": quote.get("change_pct"),
                    "volume": quote.get("volume"),
                    "amount": quote.get("amount"),
                    "high": quote.get("high"),
                    "low": quote.get("low"),
                    "open": quote.get("open"),
                    "pre_close": quote.get("pre_close"),
                    "timestamp": quote.get("timestamp"),
                }
            return {"error": f"无法获取股票 {symbol} 的行情数据"}
        except Exception as e:
            logger.error(f"获取股票行情失败: {e}")
            return {"error": str(e)}


class GetStockInfoTool(BaseTool):
    """获取公司基本信息工具"""
    name: str = "get_company_info"
    description: str = "获取公司的基本信息，包括公司名称、行业、板块、上市日期等。输入股票代码（如 600000）。"
    args_schema: Type[BaseModel] = GetStockInfoInput

    # 使用 Pydantic Field 定义字段
    user_id: str = Field(default="")
    source_router: Any = Field(default=None)

    def __init__(self, user_id: str, source_router, **kwargs):
        super().__init__(**kwargs)
        # 使用 object.__setattr__ 绕过 Pydantic 的验证
        object.__setattr__(self, 'user_id', user_id)
        object.__setattr__(self, 'source_router', source_router)
        object.__setattr__(self, '_a_stock_tool', None)

    @property
    def a_stock_tool(self):
        if self._a_stock_tool is None:
            object.__setattr__(self, '_a_stock_tool', AStockTool(user_id=self.user_id, source_router=self.source_router))
        return self._a_stock_tool

    def _run(self, symbol: str) -> Dict[str, Any]:
        """同步执行获取公司信息（由 LangChain 调用）"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在异步上下文中，创建新循环
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.a_stock_tool.get_stock_info(symbol)
                    )
                    info = future.result(timeout=30)
            else:
                info = asyncio.run(self.a_stock_tool.get_stock_info(symbol))

            if info:
                return {
                    "symbol": info.get("symbol"),
                    "name": info.get("name"),
                    "industry": info.get("industry"),
                    "sector": info.get("sector"),
                    "listing_date": info.get("listing_date"),
                    "exchange": info.get("exchange"),
                    "market": info.get("market"),
                }
            return {"error": f"无法获取股票 {symbol} 的公司信息"}
        except Exception as e:
            logger.error(f"获取公司信息失败: {e}")
            return {"error": str(e)}


class GetStockListTool(BaseTool):
    """获取股票列表工具"""
    name: str = "get_stock_list"
    description: str = "获取A股市场的股票列表，包括热门股票。可指定返回数量限制。"
    args_schema: Type[BaseModel] = GetStockListInput

    # 使用 Pydantic Field 定义字段
    user_id: str = Field(default="")
    source_router: Any = Field(default=None)

    def __init__(self, user_id: str, source_router, **kwargs):
        super().__init__(**kwargs)
        # 使用 object.__setattr__ 绕过 Pydantic 的验证
        object.__setattr__(self, 'user_id', user_id)
        object.__setattr__(self, 'source_router', source_router)
        object.__setattr__(self, '_a_stock_tool', None)

    @property
    def a_stock_tool(self):
        if self._a_stock_tool is None:
            object.__setattr__(self, '_a_stock_tool', AStockTool(user_id=self.user_id, source_router=self.source_router))
        return self._a_stock_tool

    def _run(self, limit: int = 100) -> List[Dict[str, Any]]:
        """同步执行获取股票列表（由 LangChain 调用）"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在异步上下文中，创建新循环
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.a_stock_tool.get_stock_list(limit)
                    )
                    stocks = future.result(timeout=30)
            else:
                stocks = asyncio.run(self.a_stock_tool.get_stock_list(limit))

            return stocks[:limit] if stocks else []
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []


# =============================================================================
# 工具管理器
# =============================================================================

class LocalToolsManager:
    """
    Local 工具管理器

    根据智能体配置中的 local_tools 列表，返回对应的 LangChain 工具实例。
    """

    # 工具名称到工具类的映射
    TOOL_MAPPING = {
        "get_stock_quotes": GetStockQuotesTool,
        "get_company_info": GetStockInfoTool,
        "get_stock_list": GetStockListTool,
        # TODO: 添加更多工具
        # "get_technical_indicators": GetTechnicalIndicatorsTool,
        # "get_financial_statements": GetFinancialStatementsTool,
        # "get_financial_indicators": GetFinancialIndicatorsTool,
    }

    def __init__(
        self,
        user_id: str,
        source_router: DataSourceRouter
    ):
        """
        初始化工具管理器

        Args:
            user_id: 用户 ID（用于数据隔离）
            source_router: 数据源路由器
        """
        self.user_id = user_id
        self.source_router = source_router

    def get_tools(
        self,
        tool_names: List[str]
    ) -> List[BaseTool]:
        """
        根据工具名称列表获取 LangChain 工具实例

        Args:
            tool_names: 工具名称列表（来自 YAML 配置的 local_tools）

        Returns:
            LangChain 工具列表
        """
        tools = []

        for tool_name in tool_names:
            if tool_name in self.TOOL_MAPPING:
                try:
                    tool_class = self.TOOL_MAPPING[tool_name]
                    tool = tool_class(
                        user_id=self.user_id,
                        source_router=self.source_router
                    )
                    tools.append(tool)
                    logger.debug(f"[Local Tools] 创建工具: {tool_name}")
                except Exception as e:
                    logger.error(f"[Local Tools] 创建工具失败 {tool_name}: {e}")
            else:
                logger.warning(f"[Local Tools] 未找到工具: {tool_name}")

        logger.info(f"[Local Tools] 创建了 {len(tools)} 个工具")
        return tools


# =============================================================================
# 辅助函数
# =============================================================================

def create_local_tools(
    user_id: str,
    source_router: DataSourceRouter,
    tool_names: List[str]
) -> List[BaseTool]:
    """
    创建 Local 工具列表的便捷函数

    Args:
        user_id: 用户 ID
        source_router: 数据源路由器
        tool_names: 工具名称列表

    Returns:
        LangChain 工具列表
    """
    manager = LocalToolsManager(user_id, source_router)
    return manager.get_tools(tool_names)
