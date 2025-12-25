"""
后台定时任务
使用 APScheduler 进行定时任务管理
"""
import logging
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

        # 每天凌晨 2 点执行清理任务
        sched.add_job(
            cleanup_rejected_users_task,
            CronTrigger(hour=2, minute=0),
            id="cleanup_rejected_users",
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
