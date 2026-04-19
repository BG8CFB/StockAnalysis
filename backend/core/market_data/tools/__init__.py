"""
数据工具模块

包含字段映射、数据转换、市场数据工具等
"""

from typing import Any, Dict

from core.market_data.tools.field_mapper import (
    AkShareFieldMapper,
    FieldMapper,
    TuShareFieldMapper,
)


# 延迟导入以避免循环依赖
def get_market_data_tools() -> Dict[str, Any]:
    """获取市场数据工具类（延迟导入）"""
    from core.market_data.tools.a_stock_tools import AStockTool
    from core.market_data.tools.base_tool import DataSource, MarketDataToolBase
    from core.market_data.tools.hk_stock_tools import HKStockTool
    from core.market_data.tools.us_stock_tools import USStockTool

    return {
        "MarketDataToolBase": MarketDataToolBase,
        "DataSource": DataSource,
        "AStockTool": AStockTool,
        "USStockTool": USStockTool,
        "HKStockTool": HKStockTool,
    }


__all__ = [
    # Field Mappers
    "FieldMapper",
    "TuShareFieldMapper",
    "AkShareFieldMapper",
    # Lazy loader
    "get_market_data_tools",
]
