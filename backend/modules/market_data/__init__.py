"""
市场数据模块

提供A股、美股、港股的市场数据获取、存储和查询功能。
支持多数据源（TuShare、AkShare等）和自动降级策略。
"""

from modules.market_data.api import router as market_data_router

__all__ = ["market_data_router"]
