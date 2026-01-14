"""
后台定时任务
使用 APScheduler 进行定时任务管理
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None  # type: ignore
    CronTrigger = None  # type: ignore

from core.admin.service import admin_service
from core.config import settings

logger = logging.getLogger(__name__)


# 全局调度器实例
scheduler: Optional["AsyncIOScheduler"] = None


def get_scheduler() -> "Optional[AsyncIOScheduler]":
    """获取调度器实例（单例）"""
    global scheduler
    if not APSCHEDULER_AVAILABLE:
        logger.warning("APScheduler 未安装，定时任务不可用")
        return None
    if scheduler is None:
        scheduler = AsyncIOScheduler()
    return scheduler


async def cleanup_rejected_users_task():
    """定时清理被拒绝用户任务"""
    try:
        logger.info("开始执行清理被拒绝用户任务")
        # 清理 1 天前被拒绝的用户
        count = await admin_service.cleanup_rejected_users(days=1)
        logger.info(f"清理被拒绝用户任务完成，共删除 {count} 个用户")
    except Exception as e:
        logger.error(f"清理被拒绝用户任务失败: {e}")


async def cleanup_expired_watchlist_data_task():
    """定时清理过期自选股数据任务"""
    try:
        from core.market_data.repositories.watchlist import WatchlistRepository
        from core.market_data.repositories.stock_quotes import StockQuoteRepository

        logger.info("开始执行清理过期自选股数据任务")

        # 计算截止日期（1周前）
        cutoff_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

        watchlist_repo = WatchlistRepository()
        stock_quotes_repo = StockQuoteRepository()

        # 获取所有自选股
        watchlists = await watchlist_repo.get_all_watchlists()
        total_deleted = 0

        async for watchlist in watchlists:
            symbols = watchlist.get("symbols", [])

            for symbol in symbols:
                try:
                    # 删除过期的日线数据
                    deleted = await stock_quotes_repo.delete_old_quotes(symbol, cutoff_date)
                    total_deleted += deleted
                    logger.debug(f"删除 {symbol} 的过期数据 {deleted} 条")
                except Exception as e:
                    logger.warning(f"清理 {symbol} 数据失败: {e}")

        logger.info(f"清理过期自选股数据任务完成，共删除 {total_deleted} 条记录")
    except Exception as e:
        logger.error(f"清理过期自选股数据任务失败: {e}")


async def cleanup_mcp_connection_pool_task():
    """定时清理 MCP 连接池任务"""
    try:
        from modules.mcp.pool.pool import get_mcp_connection_pool

        logger.info("开始执行清理 MCP 连接池任务")

        pool = get_mcp_connection_pool()
        result = await pool.cleanup_all(idle_threshold_seconds=3600)

        logger.info(
            f"清理 MCP 连接池任务完成，"
            f"清理连接 {result['connections_cleaned']} 个，"
            f"清理信号量 {result['semaphores_cleaned']} 个"
        )
    except Exception as e:
        logger.error(f"清理 MCP 连接池任务失败: {e}")


def init_scheduler():
    """初始化定时任务调度器"""
    if not APSCHEDULER_AVAILABLE:
        logger.warning("APScheduler 未安装，跳过定时任务初始化")
        return

    if not settings.DEBUG:
        # 仅在非调试模式下启动定时任务
        sched = get_scheduler()
        if sched is None:
            return

        # 每天凌晨 2 点执行清理被拒绝用户任务
        sched.add_job(
            cleanup_rejected_users_task,
            CronTrigger(hour=2, minute=0),
            id="cleanup_rejected_users",
            replace_existing=True,
        )

        # 每天凌晨 3 点执行清理过期自选股数据任务
        sched.add_job(
            cleanup_expired_watchlist_data_task,
            CronTrigger(hour=3, minute=0),
            id="cleanup_expired_watchlist_data",
            replace_existing=True,
        )

        # 每小时执行一次 MCP 连接池清理任务
        sched.add_job(
            cleanup_mcp_connection_pool_task,
            CronTrigger(minute=0),
            id="cleanup_mcp_connection_pool",
            replace_existing=True,
        )

        sched.start()
        logger.info("定时任务调度器已启动")
    else:
        logger.info("调试模式下不启动定时任务")


def shutdown_scheduler():
    """关闭调度器"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info("定时任务调度器已关闭")
