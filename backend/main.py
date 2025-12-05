import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.db.mongodb import mongodb
from core.db.redis import redis_connection
from core.bootstrap import module_loader
from core.exceptions import setup_exception_handlers
from core.events.schemas import EventTypes

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时的初始化
    logger.info("Starting TradingAgents-CN Backend...")

    # 连接数据库
    mongodb_connected = await mongodb.connect_to_mongodb(
        settings.mongodb_url,
        "tradingagents"
    )
    if not mongodb_connected:
        logger.error("Failed to connect to MongoDB")
        raise RuntimeError("Database connection failed")

    # 创建数据库索引
    await mongodb.create_indexes()

    # 连接Redis
    redis_connected = await redis_connection.connect_to_redis(settings.redis_url)
    if not redis_connected:
        logger.warning("Failed to connect to Redis - some features may not work")

    # 加载模块
    await module_loader.load_modules(app)

    logger.info("Application startup completed")

    yield

    # 关闭时的清理
    logger.info("Shutting down TradingAgents-CN Backend...")

    # 关闭数据库连接
    await mongodb.close_mongodb_connection()
    await redis_connection.close_redis_connection()

    logger.info("Application shutdown completed")


# 创建FastAPI应用
app = FastAPI(
    title="TradingAgents-CN API",
    description="模块化单体架构的股票分析系统",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# 设置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置异常处理器
setup_exception_handlers(app)


# 根路径
@app.get("/")
async def root():
    """根路径 - 系统状态"""
    return {
        "message": "TradingAgents-CN Backend API",
        "version": "1.0.0",
        "modules_loaded": module_loader.get_loaded_modules(),
        "debug": settings.debug
    }


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 检查数据库连接
        db = mongodb.get_database()
        await db.command('ping')

        # 检查Redis连接
        redis_client = redis_connection.get_client()
        await redis_client.ping()

        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "modules": module_loader.get_loaded_modules()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


# 模块信息端点
@app.get("/api/modules")
async def get_modules():
    """获取所有已加载模块的信息"""
    modules_info = {}
    for module_name in module_loader.get_loaded_modules():
        module_info = module_loader.get_module_info(module_name)
        if module_info:
            modules_info[module_name] = module_info.dict()
        else:
            modules_info[module_name] = {"name": module_name, "version": "unknown"}

    return {
        "modules": modules_info,
        "total_loaded": len(module_loader.get_loaded_modules())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )