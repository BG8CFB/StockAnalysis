"""
数据工具模块

包含字段映射、数据转换、市场数据工具等
"""

from core.market_data.tools.field_mapper import (
    FieldMapper,
    TuShareFieldMapper,
    AkShareFieldMapper,
)

# 延迟导入以避免循环依赖
def get_market_data_tools():
    """获取市场数据工具类（延迟导入）"""
    from core.market_data.tools.base_tool import MarketDataToolBase, DataSource
    from core.market_data.tools.a_stock_tools import AStockTool
    from core.market_data.tools.us_stock_tools import USStockTool
    from core.market_data.tools.hk_stock_tools import HKStockTool
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
