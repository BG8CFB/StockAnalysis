"""
市场数据定时任务调度器

实现定时数据同步任务，支持 A 股、美股、港股的数据定时同步。
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, time, timedelta
from enum import Enum

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    AsyncIOScheduler = None
    CronTrigger = None
    logging.warning("APScheduler not installed. Install with: pip install apscheduler")

from core.market_data.models import MarketType
from core.market_data.services.data_sync_service import DataSyncService

logger = logging.getLogger(__name__)


class ScheduleTime(str, Enum):
    """定时任务时间配置"""
    # A股市场（全量同步）
    A_STOCK_DAILY_QUOTE = "15:30"  # A股日线行情
    A_STOCK_COMPANY_INFO = "16:00"  # A股公司信息（每周一次）
    A_STOCK_FINANCIAL = "16:30"  # A股财务指标
    MARKET_NEWS = "*/30"  # 市场新闻（每30分钟）
    STOCK_LIST = "09:00"  # 股票列表（每天09:00）

    # 美股市场（仅同步自选股和核心指数）
    US_STOCK_DAILY_QUOTE = "06:00"  # 美股日线行情（美股收盘后，北京时间第二天早上）
    US_STOCK_INDEX = "06:30"  # 美股指数数据

    # 港股市场（仅同步自选股和核心指数）
    HK_STOCK_DAILY_QUOTE = "17:00"  # 港股日线行情
    HK_STOCK_INDEX = "17:30"  # 港股指数数据


class DataScheduler:
    """
    数据定时任务调度器

    负责调度市场数据的定时同步任务
    """

    def __init__(self):
        if AsyncIOScheduler is None:
            raise ImportError("APScheduler is required. Install with: pip install apscheduler")

        self.scheduler = AsyncIOScheduler()
        self.data_sync_service: Optional[DataSyncService] = None

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Data scheduler started")

    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Data scheduler shut down")

    def set_data_sync_service(self, service: DataSyncService):
        """
        设置数据同步服务

        Args:
            service: 数据同步服务实例
        """
        self.data_sync_service = service
        logger.info("Data sync service set for scheduler")

    def schedule_a_stock_daily_quote(self):
        """调度 A 股日线行情同步"""
        job_id = "a_stock_daily_quote"

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job: {job_id}")

        self.scheduler.add_job(
            self._sync_a_stock_daily_quote,
            CronTrigger.from_crontab("30 15 * * 1-5"),  # 周一到周五 15:30
            id=job_id,
            name="A股日线行情同步",
            replace_existing=True
        )
        logger.info(f"Scheduled job: {job_id} at 15:30 on weekdays")

    def schedule_a_stock_company_info(self):
        """调度 A 股公司信息同步（每周一次）"""
        job_id = "a_stock_company_info"

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job: {job_id}")

        self.scheduler.add_job(
            self._sync_a_stock_company_info,
            CronTrigger.from_crontab("0 16 * * 6"),  # 每周六 16:00
            id=job_id,
            name="A股公司信息同步",
            replace_existing=True
        )
        logger.info(f"Scheduled job: {job_id} at 16:00 on Saturday")

    def schedule_a_stock_financial(self):
        """调度 A 股财务指标同步"""
        job_id = "a_stock_financial"

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job: {job_id}")

        self.scheduler.add_job(
            self._sync_a_stock_financial,
            CronTrigger.from_crontab("30 16 * * 1-5"),  # 周一到周五 16:30
            id=job_id,
            name="A股财务指标同步",
            replace_existing=True
        )
        logger.info(f"Scheduled job: {job_id} at 16:30 on weekdays")

    def schedule_market_news(self):
        """调度市场新闻同步"""
        job_id = "market_news"

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job: {job_id}")

        self.scheduler.add_job(
            self._sync_market_news,
            CronTrigger.from_crontab("*/30 * * * *"),  # 每30分钟
            id=job_id,
            name="市场新闻同步",
            replace_existing=True
        )
        logger.info(f"Scheduled job: {job_id} every 30 minutes")

    def schedule_stock_list(self):
        """调度股票列表同步"""
        job_id = "stock_list"

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job: {job_id}")

        self.scheduler.add_job(
            self._sync_stock_list,
            CronTrigger.from_crontab("0 9 * * 1-5"),  # 周一到周五 09:00
            id=job_id,
            name="股票列表同步",
            replace_existing=True
        )
        logger.info(f"Scheduled job: {job_id} at 09:00 on weekdays")

    def schedule_us_stock_daily_quote(self):
        """调度美股日线行情同步（仅自选股和核心指数）"""
        job_id = "us_stock_daily_quote"

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job: {job_id}")

        self.scheduler.add_job(
            self._sync_us_stock_daily_quote,
            CronTrigger.from_crontab("0 6 * * 1-5"),  # 周一到周五 06:00
            id=job_id,
            name="美股日线行情同步",
            replace_existing=True
        )
        logger.info(f"Scheduled job: {job_id} at 06:00 on weekdays")

    def schedule_us_stock_index(self):
        """调度美股指数数据同步"""
        job_id = "us_stock_index"

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job: {job_id}")

        self.scheduler.add_job(
            self._sync_us_stock_index,
            CronTrigger.from_crontab("30 6 * * 1-5"),  # 周一到周五 06:30
            id=job_id,
            name="美股指数数据同步",
            replace_existing=True
        )
        logger.info(f"Scheduled job: {job_id} at 06:30 on weekdays")

    def schedule_hk_stock_daily_quote(self):
        """调度港股日线行情同步（仅自选股和核心指数）"""
        job_id = "hk_stock_daily_quote"

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job: {job_id}")

        self.scheduler.add_job(
            self._sync_hk_stock_daily_quote,
            CronTrigger.from_crontab("0 17 * * 1-5"),  # 周一到周五 17:00
            id=job_id,
            name="港股日线行情同步",
            replace_existing=True
        )
        logger.info(f"Scheduled job: {job_id} at 17:00 on weekdays")

    def schedule_hk_stock_index(self):
        """调度港股指数数据同步"""
        job_id = "hk_stock_index"

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job: {job_id}")

        self.scheduler.add_job(
            self._sync_hk_stock_index,
            CronTrigger.from_crontab("30 17 * * 1-5"),  # 周一到周五 17:30
            id=job_id,
            name="港股指数数据同步",
            replace_existing=True
        )
        logger.info(f"Scheduled job: {job_id} at 17:30 on weekdays")

    def schedule_data_cleanup(self):
        """调度数据清理任务"""
        job_id = "data_cleanup"

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing job: {job_id}")

        self.scheduler.add_job(
            self._cleanup_expired_data,
            CronTrigger.from_crontab("0 3 * * *"),  # 每天凌晨 3:00
            id=job_id,
            name="过期数据清理",
            replace_existing=True
        )
        logger.info(f"Scheduled job: {job_id} at 03:00 daily")

    def schedule_all_jobs(self):
        """调度所有定时任务"""
        logger.info("Scheduling all data sync jobs...")

        # A股市场（全量同步）
        self.schedule_stock_list()
        self.schedule_a_stock_daily_quote()
        self.schedule_a_stock_company_info()
        self.schedule_a_stock_financial()
        self.schedule_market_news()

        # 美股市场（仅自选股）
        self.schedule_us_stock_daily_quote()
        self.schedule_us_stock_index()

        # 港股市场（仅自选股）
        self.schedule_hk_stock_daily_quote()
        self.schedule_hk_stock_index()

        # 数据清理任务
        self.schedule_data_cleanup()

        logger.info("All data sync jobs scheduled successfully")

    def remove_all_jobs(self):
        """移除所有定时任务"""
        self.scheduler.remove_all_jobs()
        logger.info("All scheduled jobs removed")

    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """获取所有已调度的任务"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            })
        return jobs

    # ==================== 任务执行函数 ====================

    async def _sync_a_stock_daily_quote(self):
        """执行 A 股日线行情同步"""
        try:
            if not self.data_sync_service:
                logger.warning("Data sync service not set, skipping A stock daily quote sync")
                return

            logger.info("Starting A stock daily quote sync")

            # 获取所有 A 股股票列表
            from ...repositories.stock_info import StockInfoRepository
            stock_repo = StockInfoRepository()
            # 移除 limit=5000 限制，获取所有股票
            stocks = await stock_repo.get_by_market(MarketType.A_STOCK)

            if not stocks:
                logger.warning("No A stocks found for daily quote sync")
                return

            symbols = [s["symbol"] for s in stocks]

            # 同步当日行情
            today = datetime.now().strftime("%Y%m%d")
            # 使用带自动降级的同步方法
            result = await self.data_sync_service.sync_daily_quotes_with_fallback(
                symbols=symbols,
                start_date=today,
                end_date=today
            )

            logger.info(f"A stock daily quote sync completed: {result}")

        except Exception as e:
            logger.error(f"Failed to sync A stock daily quotes: {e}")

    async def _sync_market_news(self):
        """执行市场新闻同步"""
        try:
            if not self.data_sync_service:
                logger.warning("Data sync service not set, skipping market news sync")
                return

            logger.info("Starting market news sync")

            # 优先使用 TuShare (sina源)
            result = await self.data_sync_service.sync_market_news(
                source_id="tushare",
                limit=100
            )
            
            # 如果 TuShare 失败或数据为空，尝试 AkShare (eastmoney/cls)
            if result.get("status") == "failed" or result.get("result", {}).get("upserted", 0) == 0:
                logger.info("TuShare news sync empty or failed, trying AkShare")
                result = await self.data_sync_service.sync_market_news(
                    source_id="akshare",
                    limit=50
                )

            logger.info(f"Market news sync completed: {result}")

        except Exception as e:
            logger.error(f"Failed to sync market news: {e}")

    async def _sync_stock_list(self):
        """执行股票列表同步"""
        try:
            if not self.data_sync_service:
                logger.warning("Data sync service not set, skipping stock list sync")
                return

            logger.info("Starting stock list sync")

            result = await self.data_sync_service.sync_stock_list_with_fallback(
                market=MarketType.A_STOCK
            )

            logger.info(f"Stock list sync completed: {result}")

        except Exception as e:
            logger.error(f"Failed to sync stock list: {e}")

    async def _sync_a_stock_company_info(self):
        """执行 A 股公司信息同步"""
        try:
            if not self.data_sync_service:
                logger.warning("Data sync service not set, skipping A stock company info sync")
                return

            logger.info("Starting A stock company info sync")

            # 获取所有 A 股股票列表
            from ...repositories.stock_info import StockInfoRepository
            stock_repo = StockInfoRepository()
            stocks = await stock_repo.get_by_market(MarketType.A_STOCK, limit=5000)

            if not stocks:
                logger.warning("No A stocks found for company info sync")
                return

            symbols = [s["symbol"] for s in stocks]

            # 同步公司信息
            result = await self.data_sync_service.sync_company_info(
                symbols=symbols,
                source_id="tushare"
            )

            logger.info(f"A stock company info sync completed: {result}")

        except Exception as e:
            logger.error(f"Failed to sync A stock company info: {e}")

    async def _sync_a_stock_financial(self):
        """执行 A 股财务指标同步"""
        try:
            if not self.data_sync_service:
                logger.warning("Data sync service not set, skipping A stock financial sync")
                return

            logger.info("Starting A stock financial indicators sync")

            # 获取所有 A 股股票列表
            from ...repositories.stock_info import StockInfoRepository
            stock_repo = StockInfoRepository()
            stocks = await stock_repo.get_by_market(MarketType.A_STOCK, limit=1000)

            if not stocks:
                logger.warning("No A stocks found for financial sync")
                return

            symbols = [s["symbol"] for s in stocks]

            # 同步财务指标
            # 使用带自动降级的同步方法
            result = await self.data_sync_service.sync_financials_with_fallback(
                symbols=symbols
            )

            logger.info(f"A stock financial indicators sync completed: {result}")

        except Exception as e:
            logger.error(f"Failed to sync A stock financial indicators: {e}")

    async def _sync_us_stock_daily_quote(self):
        """执行美股日线行情同步（仅自选股）"""
        try:
            if not self.data_sync_service:
                logger.warning("Data sync service not set, skipping US stock daily quote sync")
                return

            logger.info("Starting US stock daily quote sync (watchlist only)")

            # 获取自选股列表
            from ...repositories.watchlist import UserWatchlistRepository
            watchlist_repo = UserWatchlistRepository()

            # 获取所有用户的自选股
            watchlists = await watchlist_repo.get_all_watchlists()

            if not watchlists:
                logger.warning("No watchlists found for US stock daily quote sync")
                return

            # 收集所有美股自选股
            us_symbols = set()
            for wl in watchlists:
                for stock in wl.get("stocks", []):
                    symbol = stock.get("symbol", "")
                    if symbol.endswith(".US"):
                        us_symbols.add(symbol)

            if not us_symbols:
                logger.warning("No US stocks in watchlists for daily quote sync")
                return

            # 同步当日行情
            today = datetime.now().strftime("%Y%m%d")
            result = await self.data_sync_service.sync_daily_quotes(
                symbols=list(us_symbols),
                start_date=today,
                end_date=today,
                source_id="yahoo"
            )

            logger.info(f"US stock daily quote sync completed: {result}")

        except Exception as e:
            logger.error(f"Failed to sync US stock daily quotes: {e}")

    async def _sync_us_stock_index(self):
        """执行美股指数数据同步"""
        try:
            if not self.data_sync_service:
                logger.warning("Data sync service not set, skipping US stock index sync")
                return

            logger.info("Starting US stock index sync")

            # 美股核心指数代码
            index_symbols = [
                "^GSPC.US",  # S&P 500
                "^DJI.US",   # 道琼斯
                "^IXIC.US",  # 纳斯达克
            ]

            # 同步指数行情
            today = datetime.now().strftime("%Y%m%d")
            result = await self.data_sync_service.sync_daily_quotes(
                symbols=index_symbols,
                start_date=today,
                end_date=today,
                source_id="yahoo"
            )

            logger.info(f"US stock index sync completed: {result}")

        except Exception as e:
            logger.error(f"Failed to sync US stock index: {e}")

    async def _sync_hk_stock_daily_quote(self):
        """执行港股日线行情同步（仅自选股）"""
        try:
            if not self.data_sync_service:
                logger.warning("Data sync service not set, skipping HK stock daily quote sync")
                return

            logger.info("Starting HK stock daily quote sync (watchlist only)")

            # 获取自选股列表
            from ...repositories.watchlist import UserWatchlistRepository
            watchlist_repo = UserWatchlistRepository()

            # 获取所有用户的自选股
            watchlists = await watchlist_repo.get_all_watchlists()

            if not watchlists:
                logger.warning("No watchlists found for HK stock daily quote sync")
                return

            # 收集所有港股自选股
            hk_symbols = set()
            for wl in watchlists:
                for stock in wl.get("stocks", []):
                    symbol = stock.get("symbol", "")
                    if symbol.endswith(".HK"):
                        hk_symbols.add(symbol)

            if not hk_symbols:
                logger.warning("No HK stocks in watchlists for daily quote sync")
                return

            # 同步当日行情
            today = datetime.now().strftime("%Y%m%d")
            result = await self.data_sync_service.sync_daily_quotes(
                symbols=list(hk_symbols),
                start_date=today,
                end_date=today,
                source_id="akshare",
                market="HK_STOCK"
            )

            logger.info(f"HK stock daily quote sync completed: {result}")

        except Exception as e:
            logger.error(f"Failed to sync HK stock daily quotes: {e}")

    async def _sync_hk_stock_index(self):
        """执行港股指数数据同步"""
        try:
            if not self.data_sync_service:
                logger.warning("Data sync service not set, skipping HK stock index sync")
                return

            logger.info("Starting HK stock index sync")

            # 港股核心指数代码
            index_symbols = [
                "^HSI.HK",  # 恒生指数
            ]

            # 同步指数行情
            today = datetime.now().strftime("%Y%m%d")
            result = await self.data_sync_service.sync_daily_quotes(
                symbols=index_symbols,
                start_date=today,
                end_date=today,
                source_id="akshare"
            )

            logger.info(f"HK stock index sync completed: {result}")

        except Exception as e:
            logger.error(f"Failed to sync HK stock index: {e}")

    async def _cleanup_expired_data(self):
        """执行过期数据清理"""
        try:
            logger.info("Starting expired data cleanup")

            # 清理过期的当日行情数据（保留1周）
            await self._cleanup_daily_quotes(days=7)

            # 清理过期的分钟K线数据（保留1周）
            await self._cleanup_minute_klines(days=7)

            # 清理过期的数据源状态历史（保留90天）
            await self._cleanup_status_history(days=90)

            logger.info("Expired data cleanup completed")

        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")

    async def _cleanup_daily_quotes(self, days: int = 7):
        """
        清理过期的当日行情数据

        Args:
            days: 保留天数
        """
        try:
            from ...repositories.stock_quotes import StockQuoteRepository
            quote_repo = StockQuoteRepository()

            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

            # 删除过期的当日行情（仅删除非历史数据）
            deleted_count = await quote_repo.delete_expired_intraday_quotes(cutoff_date)

            logger.info(f"Cleaned up {deleted_count} expired daily quotes older than {cutoff_date}")

        except Exception as e:
            logger.error(f"Failed to cleanup daily quotes: {e}")

    async def _cleanup_minute_klines(self, days: int = 7):
        """
        清理过期的分钟K线数据

        Args:
            days: 保留天数
        """
        try:
            from ...repositories.stock_quotes import StockQuoteRepository
            quote_repo = StockQuoteRepository()

            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

            # 删除过期的分钟K线
            deleted_count = await quote_repo.delete_expired_minute_klines(cutoff_date)

            logger.info(f"Cleaned up {deleted_count} expired minute klines older than {cutoff_date}")

        except Exception as e:
            logger.error(f"Failed to cleanup minute klines: {e}")

    async def _cleanup_status_history(self, days: int = 90):
        """
        清理过期的数据源状态历史

        Args:
            days: 保留天数
        """
        try:
            from ...repositories.datasource import DataSourceStatusHistoryRepository
            history_repo = DataSourceStatusHistoryRepository()

            deleted_count = await history_repo.cleanup_old_history(days=days)

            logger.info(f"Cleaned up {deleted_count} expired status history records older than {days} days")

        except Exception as e:
            logger.error(f"Failed to cleanup status history: {e}")


# 全局调度器实例
_global_scheduler: Optional[DataScheduler] = None


def get_data_scheduler() -> DataScheduler:
    """
    获取全局数据调度器实例

    Returns:
        数据调度器实例
    """
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = DataScheduler()
        logger.info("Created global data scheduler")
    return _global_scheduler
