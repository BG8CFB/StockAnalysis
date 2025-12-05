import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="TradingAgents-CN API",
    description="模块化单体架构的股票分析系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 设置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 根路径
@app.get("/")
async def root():
    """根路径 - 系统状态"""
    return {
        "message": "TradingAgents-CN Backend API",
        "version": "1.0.0",
        "debug": True
    }

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "message": "Service is running"
    }

# 模拟仪表盘数据
@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """获取仪表盘概览数据"""
    return {
        "system_stats": {
            "total_users": 1247,
            "active_users": 89,
            "total_stocks_analyzed": 15420,
            "analysis_requests_today": 342
        },
        "portfolio_summary": {
            "total_value": 156789.32,
            "daily_change": 2345.67,
            "daily_change_percent": 1.52,
            "total_return": 12890.45,
            "total_return_percent": 8.96
        },
        "market_overview": {
            "market_status": "open",
            "major_indices": [
                {
                    "name": "上证指数",
                    "value": 3124.67,
                    "change": 15.23,
                    "change_percent": 0.49
                },
                {
                    "name": "深证成指",
                    "value": 10234.56,
                    "change": -23.45,
                    "change_percent": -0.23
                }
            ]
        },
        "recent_activities": [
            {
                "id": "1",
                "type": "analysis_completed",
                "title": "股票分析完成",
                "description": "贵州茅台 (600519) 分析报告已生成",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )