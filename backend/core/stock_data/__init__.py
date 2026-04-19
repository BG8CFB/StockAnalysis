"""
股票数据查询 API 模块

暴露 /api/stocks/* 和 /api/stock-data/* 端点，委托现有 market_data 模块。
"""

from core.stock_data.api import stock_data_router, stocks_router

__all__ = ["stocks_router", "stock_data_router"]
