"""
Local 工具适配器

将项目内部的 Market Data 工具转换为 LangChain 可用的 BaseTool 格式。
支持 A 股、港股、美股多市场。

**版本**: v2.0
**最后更新**: 2026-02-10
"""

import logging
from typing import Optional, List, Dict, Any, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from core.market_data.models import MarketType
from core.market_data.managers.source_router import DataSourceRouter

logger = logging.getLogger(__name__)


# =============================================================================
# LangChain 工具输入模式（添加市场类型）
# =============================================================================

class GetStockQuotesInput(BaseModel):
    """获取股票行情输入参数"""
    symbol: str = Field(description="股票代码，如 600000 或 000001")
    market: str = Field(default="A_STOCK", description="市场类型: A_STOCK, HK_STOCK, US_STOCK")


class GetStockInfoInput(BaseModel):
    """获取公司信息输入参数"""
    symbol: str = Field(description="股票代码，如 600000 或 000001")
    market: str = Field(default="A_STOCK", description="市场类型: A_STOCK, HK_STOCK, US_STOCK")


class GetStockListInput(BaseModel):
    """获取股票列表输入参数"""
    limit: int = Field(default=100, description="返回数量限制")
    market: str = Field(default="A_STOCK", description="市场类型: A_STOCK, HK_STOCK, US_STOCK")


# =============================================================================
# 工具工厂函数（根据市场类型选择正确的工具类）
# =============================================================================

def get_tool_class_for_market(market: str) -> type:
    """
    根据市场类型获取对应的工具类

    Args:
        market: 市场类型字符串 (A_STOCK, HK_STOCK, US_STOCK)

    Returns:
        对应的工具类
    """
    market_type = MarketType(market) if market in [e.value for e in MarketType] else MarketType.A_STOCK

    if market_type == MarketType.HK_STOCK:
        from core.market_data.tools.hk_stock_tools import HKStockTool
        return HKStockTool
    elif market_type == MarketType.US_STOCK:
        from core.market_data.tools.us_stock_tools import USStockTool
        return USStockTool
    else:
        from core.market_data.tools.a_stock_tools import AStockTool
        return AStockTool


# =============================================================================
# LangChain 工具实现（多市场通用版）
# =============================================================================

class GetStockQuotesTool(BaseTool):
    """获取股票实时行情工具（支持多市场）"""
    name: str = "get_stock_quotes"
    description: str = """获取股票的实时行情数据，包括价格、成交量、涨跌幅等。
    - A股输入格式：600000 或 600000.SH/600000.SZ
    - 港股输入格式：0700 或 0700.HK
    - 美股输入格式：AAPL 或 AAPL.US"""
    args_schema: Type[BaseModel] = GetStockQuotesInput

    # 使用 Pydantic Field 定义字段
    user_id: str = Field(default="")
    source_router: Any = Field(default=None)
    market: str = Field(default="A_STOCK")

    def __init__(self, user_id: str, source_router, market: str = "A_STOCK", **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'user_id', user_id)
        object.__setattr__(self, 'source_router', source_router)
        object.__setattr__(self, 'market', market)
        object.__setattr__(self, '_tool_instance', None)

    @property
    def tool_instance(self):
        """懒加载对应的工具实例"""
        if self._tool_instance is None:
            tool_class = get_tool_class_for_market(self.market)
            object.__setattr__(self, '_tool_instance', tool_class(
                user_id=self.user_id,
                source_router=self.source_router
            ))
        return self._tool_instance

    async def _arun(self, symbol: str, market: str = "A_STOCK") -> Dict[str, Any]:
        """异步执行获取行情（LangChain 优先调用此方法）"""
        try:
            if market != self.market:
                tool_class = get_tool_class_for_market(market)
                tool = tool_class(user_id=self.user_id, source_router=self.source_router)
            else:
                tool = self.tool_instance

            quote = await tool.get_realtime_quote(symbol)
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
                    "market": market,
                }
            return {"error": f"无法获取股票 {symbol} ({market}) 的行情数据"}
        except Exception as e:
            logger.error(f"获取股票行情失败: {e}")
            return {"error": str(e)}

    def _run(self, symbol: str, market: str = "A_STOCK") -> Dict[str, Any]:
        """同步执行（回退方案，非异步上下文使用）"""
        import asyncio
        try:
            return asyncio.run(self._arun(symbol, market))
        except RuntimeError:
            # 已在运行的事件循环中不能再调用 asyncio.run，返回错误
            return {"error": "无法在同步上下文中调用异步工具，请通过异步接口调用"}


class GetStockInfoTool(BaseTool):
    """获取公司基本信息工具（支持多市场）"""
    name: str = "get_company_info"
    description: str = """获取公司的基本信息，包括公司名称、行业、板块、上市日期等。
    - A股输入格式：600000
    - 港股输入格式：0700
    - 美股输入格式：AAPL"""
    args_schema: Type[BaseModel] = GetStockInfoInput

    user_id: str = Field(default="")
    source_router: Any = Field(default=None)
    market: str = Field(default="A_STOCK")

    def __init__(self, user_id: str, source_router, market: str = "A_STOCK", **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'user_id', user_id)
        object.__setattr__(self, 'source_router', source_router)
        object.__setattr__(self, 'market', market)
        object.__setattr__(self, '_tool_instance', None)

    @property
    def tool_instance(self):
        if self._tool_instance is None:
            tool_class = get_tool_class_for_market(self.market)
            object.__setattr__(self, '_tool_instance', tool_class(
                user_id=self.user_id,
                source_router=self.source_router
            ))
        return self._tool_instance

    async def _arun(self, symbol: str, market: str = "A_STOCK") -> Dict[str, Any]:
        """异步执行获取公司信息"""
        try:
            if market != self.market:
                tool_class = get_tool_class_for_market(market)
                tool = tool_class(user_id=self.user_id, source_router=self.source_router)
            else:
                tool = self.tool_instance

            info = await tool.get_stock_info(symbol)
            if info:
                return {
                    "symbol": info.get("symbol"),
                    "name": info.get("name"),
                    "industry": info.get("industry"),
                    "sector": info.get("sector"),
                    "listing_date": info.get("listing_date"),
                    "exchange": info.get("exchange"),
                    "market": info.get("market") or market,
                }
            return {"error": f"无法获取股票 {symbol} ({market}) 的公司信息"}
        except Exception as e:
            logger.error(f"获取公司信息失败: {e}")
            return {"error": str(e)}

    def _run(self, symbol: str, market: str = "A_STOCK") -> Dict[str, Any]:
        """同步执行（回退方案）"""
        import asyncio
        try:
            return asyncio.run(self._arun(symbol, market))
        except RuntimeError:
            return {"error": "无法在同步上下文中调用异步工具，请通过异步接口调用"}


class GetStockListTool(BaseTool):
    """获取股票列表工具（支持多市场）"""
    name: str = "get_stock_list"
    description: str = """获取指定市场的股票列表，包括热门股票。
    - A_STOCK: A股市场
    - HK_STOCK: 港股市场
    - US_STOCK: 美股市场"""
    args_schema: Type[BaseModel] = GetStockListInput

    user_id: str = Field(default="")
    source_router: Any = Field(default=None)
    market: str = Field(default="A_STOCK")

    def __init__(self, user_id: str, source_router, market: str = "A_STOCK", **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'user_id', user_id)
        object.__setattr__(self, 'source_router', source_router)
        object.__setattr__(self, 'market', market)
        object.__setattr__(self, '_tool_instance', None)

    @property
    def tool_instance(self):
        if self._tool_instance is None:
            tool_class = get_tool_class_for_market(self.market)
            object.__setattr__(self, '_tool_instance', tool_class(
                user_id=self.user_id,
                source_router=self.source_router
            ))
        return self._tool_instance

    async def _arun(self, limit: int = 100, market: str = "A_STOCK") -> List[Dict[str, Any]]:
        """异步执行获取股票列表"""
        try:
            if market != self.market:
                tool_class = get_tool_class_for_market(market)
                tool = tool_class(user_id=self.user_id, source_router=self.source_router)
            else:
                tool = self.tool_instance

            stocks = await tool.get_stock_list(limit)
            return stocks[:limit] if stocks else []
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []

    def _run(self, limit: int = 100, market: str = "A_STOCK") -> List[Dict[str, Any]]:
        """同步执行（回退方案）"""
        import asyncio
        try:
            return asyncio.run(self._arun(limit, market))
        except RuntimeError:
            return []


# =============================================================================
# 工具管理器
# =============================================================================

class LocalToolsManager:
    """
    Local 工具管理器

    根据智能体配置中的 local_tools 列表，返回对应的 LangChain 工具实例。
    支持多市场动态选择。
    """

    # 工具名称到工具类的映射（基础映射，实际使用时会根据 market 调整）
    TOOL_MAPPING = {
        "get_stock_quotes": GetStockQuotesTool,
        "get_company_info": GetStockInfoTool,
        "get_stock_list": GetStockListTool,
    }

    def __init__(
        self,
        user_id: str,
        source_router: DataSourceRouter,
        market: str = "A_STOCK"
    ):
        """
        初始化工具管理器

        Args:
            user_id: 用户 ID（用于数据隔离）
            source_router: 数据源路由器
            market: 市场类型 (A_STOCK, HK_STOCK, US_STOCK)
        """
        self.user_id = user_id
        self.source_router = source_router
        self.market = market

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
                        source_router=self.source_router,
                        market=self.market  # 传递市场类型
                    )
                    tools.append(tool)
                    logger.debug(f"[Local Tools] 创建工具: {tool_name} (market={self.market})")
                except Exception as e:
                    logger.error(f"[Local Tools] 创建工具失败 {tool_name}: {e}")
            else:
                logger.warning(f"[Local Tools] 未找到工具: {tool_name}")

        logger.info(f"[Local Tools] 为 {self.market} 创建了 {len(tools)} 个工具")
        return tools


# =============================================================================
# 辅助函数
# =============================================================================

def create_local_tools(
    user_id: str,
    source_router: DataSourceRouter,
    tool_names: List[str],
    market: str = "A_STOCK"
) -> List[BaseTool]:
    """
    创建 Local 工具列表的便捷函数

    Args:
        user_id: 用户 ID
        source_router: 数据源路由器
        tool_names: 工具名称列表
        market: 市场类型 (A_STOCK, HK_STOCK, US_STOCK)

    Returns:
        LangChain 工具列表
    """
    manager = LocalToolsManager(user_id, source_router, market)
    return manager.get_tools(tool_names)
