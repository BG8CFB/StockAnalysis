"""
API 兼容层

为前端路径提供适配器路由，内部委托给现有模块服务。
"""

from .analysis_router import router as analysis_router
from .analysis_router import stream_router as analysis_stream_router
from .reports_router import router as reports_router

__all__ = ["analysis_router", "analysis_stream_router", "reports_router"]
