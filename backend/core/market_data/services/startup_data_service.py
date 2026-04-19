"""
启动时数据检查和补录服务

负责在应用启动时检查数据完整性，并自动补录缺失的数据。

功能：
1. 首次启动检测：检测数据库是否为空，触发首次全量同步
2. 数据缺失检测：检查最后同步时间，判断是否需要补录
3. 智能补录：根据缺失情况自动补录数据
4. 数据源状态初始化：为所有配置的数据源创建初始状态记录
"""

import logging
from datetime import date as date_type
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.market_data.models import MarketType
from core.market_data.models.datasource import (
    DataSourceHealthStatus,
    DataSourceStatus,
    DataSourceType,
)
from core.market_data.services.data_sync_service import DataSyncService

logger = logging.getLogger(__name__)


class StartupDataService:
    """启动时数据检查和补录服务"""

    def __init__(self, data_sync_service: DataSyncService):
        """
        初始化启动数据服务

        Args:
            data_sync_service: 数据同步服务实例
        """
        self.data_sync_service = data_sync_service
        self.stock_info_repo: Optional[Any] = None
        self.stock_quotes_repo: Optional[Any] = None
        self.stock_financial_repo: Optional[Any] = None
        self.stock_indicator_repo: Optional[Any] = None
        self.stock_company_repo: Optional[Any] = None

    async def check_and_catchup(self) -> Dict[str, Any]:
        """
        执行启动时数据检查和补录

        Returns:
            检查和补录结果
        """
        logger.info("=" * 60)
        logger.info("📊 开始启动时数据检查和补录")
        logger.info("=" * 60)

        result = {"is_first_startup": False, "tasks_triggered": [], "total_catchup_records": 0}

        try:
            # 延迟加载 repository（避免循环导入）
            await self._load_repositories()

            # 1. 初始化数据源状态（新增）
            await self._initialize_data_source_status(result)

            # 2. 检查是否首次启动
            is_first_startup = await self._check_is_first_startup()
            result["is_first_startup"] = is_first_startup

            if is_first_startup:
                logger.info("🔍 检测到首次启动，将执行首次全量同步")
                await self._perform_first_sync(result)
            else:
                logger.info("🔍 检测到非首次启动，检查数据缺失情况")
                await self._check_and_catchup_missing_data(result)

            logger.info("=" * 60)
            tasks = result.get("tasks_triggered", [])
            task_count = len(tasks) if isinstance(tasks, list) else 0
            logger.info(f"启动数据检查完成，触发 {task_count} 个补录任务")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 启动数据检查失败: {e}", exc_info=True)
            result["error"] = str(e)

        return result

    async def _load_repositories(self) -> None:
        """延迟加载 repository"""
        from core.market_data.repositories.stock_company import StockCompanyRepository
        from core.market_data.repositories.stock_financial import (
            StockFinancialIndicatorRepository,
            StockFinancialRepository,
        )
        from core.market_data.repositories.stock_info import StockInfoRepository
        from core.market_data.repositories.stock_quotes import StockQuoteRepository

        self.stock_info_repo = StockInfoRepository()
        self.stock_quotes_repo = StockQuoteRepository()
        self.stock_financial_repo = StockFinancialRepository()
        self.stock_indicator_repo = StockFinancialIndicatorRepository()
        self.stock_company_repo = StockCompanyRepository()

    async def _check_is_first_startup(self) -> bool:
        """
        检查是否首次启动

        Returns:
            是否首次启动
        """
        # 检查是否有任何股票信息
        assert self.stock_info_repo is not None, "stock_info_repo not initialized"
        count: int = await self.stock_info_repo.count_documents({})
        return count == 0

    async def _perform_first_sync(self, result: Dict[str, Any]) -> None:
        """
        执行首次全量同步（使用自动降级逻辑）

        Args:
            result: 结果字典
        """
        logger.info("🚀 开始首次全量同步...")

        # 1. 同步A股股票列表（自动降级到可用数据源）
        try:
            logger.info("  📋 同步A股股票列表（自动降级）...")
            # 使用数据源路由器，自动尝试 tushare -> akshare
            sync_result = await self.data_sync_service.sync_stock_list_with_fallback(
                market=MarketType.A_STOCK, status="L"
            )
            result["tasks_triggered"].append(
                {
                    "task": "sync_stock_list",
                    "status": sync_result["status"],
                    "records": sync_result.get("result", {}).get("total", 0),
                    "source": sync_result.get("result", {}).get("source", "unknown"),
                }
            )
            logger.info(
                f"  ✅ A股股票列表同步完成: "
                f"{sync_result.get('result', {}).get('total', 0)} 条 "
                f"(数据源: {sync_result.get('result', {}).get('source', 'unknown')})"
            )
        except Exception as e:
            logger.error(f"  ❌ A股股票列表同步失败: {e}")
            result["tasks_triggered"].append(
                {"task": "sync_stock_list", "status": "failed", "error": str(e)}
            )

        # 2. 同步最近的A股日线数据（最近1个月）
        try:
            logger.info("  📈 同步A股最近1个月日线数据...")
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

            # 获取股票列表（限制前100只，避免首次同步时间过长）
            assert self.stock_info_repo is not None, "stock_info_repo not initialized"
            stocks = await self.stock_info_repo.get_by_market(MarketType.A_STOCK, limit=100)
            symbols = [s["symbol"] for s in stocks]

            if symbols:
                sync_result = await self.data_sync_service.sync_daily_quotes_with_fallback(
                    symbols=symbols, start_date=start_date, end_date=end_date
                )
                result["tasks_triggered"].append(
                    {
                        "task": "sync_daily_quotes_initial",
                        "status": sync_result["status"],
                        "records": sync_result.get("result", {}).get("total_quotes", 0),
                        "source": sync_result.get("result", {}).get("source", "unknown"),
                    }
                )
                logger.info(
                    f"  ✅ A股日线数据同步完成: "
                    f"{sync_result.get('result', {}).get('total_quotes', 0)} 条 "
                    f"(数据源: {sync_result.get('result', {}).get('source', 'unknown')})"
                )
        except Exception as e:
            logger.error(f"  ❌ A股日线数据同步失败: {e}")
            result["tasks_triggered"].append(
                {"task": "sync_daily_quotes_initial", "status": "failed", "error": str(e)}
            )

        # 3. 同步A股公司信息
        try:
            logger.info("  🏢 同步A股公司信息...")
            assert self.stock_info_repo is not None, "stock_info_repo not initialized"
            stocks = await self.stock_info_repo.get_by_market(MarketType.A_STOCK, limit=50)
            symbols = [s["symbol"] for s in stocks]

            if symbols:
                sync_result = await self.data_sync_service.sync_company_info_with_fallback(
                    symbols=symbols
                )
                result["tasks_triggered"].append(
                    {
                        "task": "sync_company_info_initial",
                        "status": sync_result["status"],
                        "records": sync_result.get("result", {}).get("total_records", 0),
                        "source": sync_result.get("result", {}).get("source", "unknown"),
                    }
                )
                logger.info(
                    f"  ✅ A股公司信息同步完成: "
                    f"{sync_result.get('result', {}).get('total_records', 0)} 条 "
                    f"(数据源: {sync_result.get('result', {}).get('source', 'unknown')})"
                )
        except Exception as e:
            logger.error(f"  ❌ A股公司信息同步失败: {e}")
            result["tasks_triggered"].append(
                {"task": "sync_company_info_initial", "status": "failed", "error": str(e)}
            )

    async def _check_and_catchup_missing_data(self, result: Dict[str, Any]) -> None:
        """
        检查并补录缺失数据

        Args:
            result: 结果字典
        """
        # 1. 检查A股股票列表（超过7天未更新）
        await self._check_and_catchup_stock_list(result)

        # 2. 检查A股日线行情（缺失交易日）
        await self._check_and_catchup_daily_quotes(result)

        # 3. 检查A股公司信息（超过7天未更新）
        await self._check_and_catchup_company_info(result)

        # 4. 检查A股财务数据（超过30天未更新）
        await self._check_and_catchup_financials(result)

    async def _check_and_catchup_stock_list(self, result: Dict[str, Any]) -> None:
        """检查并补录A股股票列表"""
        try:
            # 获取最新的股票信息更新时间
            assert self.stock_info_repo is not None, "stock_info_repo not initialized"
            stocks = await self.stock_info_repo.find_many(
                {"market": "A_STOCK"}, sort=[("updated_at", -1)], limit=1
            )
            latest_stock = stocks[0] if stocks else None

            if not latest_stock:
                logger.warning("  ⚠️ 未找到A股股票信息，跳过股票列表补录检查")
                return

            last_update = latest_stock.get("updated_at")
            if not last_update:
                return

            # 计算距离上次更新的天数
            days_since_update = (datetime.now() - last_update).days

            # 如果超过7天未更新，触发更新
            if days_since_update > 7:
                logger.info(f"  📋 A股股票列表超过 {days_since_update} 天未更新，触发补录")

                sync_result = await self.data_sync_service.sync_stock_list_with_fallback(
                    market=MarketType.A_STOCK, status="L"
                )

                result["tasks_triggered"].append(
                    {
                        "task": "catchup_stock_list",
                        "status": sync_result["status"],
                        "records": sync_result.get("result", {}).get("total", 0),
                        "reason": f"超过{days_since_update}天未更新",
                    }
                )

                logger.info(
                    f"  ✅ A股股票列表补录完成: {sync_result.get('result', {}).get('total', 0)} 条"
                )
            else:
                logger.info(f"  ✅ A股股票列表最新，距上次更新 {days_since_update} 天")

        except Exception as e:
            logger.error(f"  ❌ A股股票列表检查失败: {e}")

    async def _check_and_catchup_daily_quotes(self, result: Dict[str, Any]) -> None:
        """检查并补录A股日线行情"""
        try:
            # 获取最新的日线数据日期
            assert self.stock_quotes_repo is not None, "stock_quotes_repo not initialized"
            latest_quotes = await self.stock_quotes_repo.find_many(
                {"market": "A_STOCK"}, sort=[("trade_date", -1)], limit=1
            )
            latest_quote = latest_quotes[0] if latest_quotes else None

            if not latest_quote:
                logger.warning("  ⚠️ 未找到A股日线数据，跳过日线补录检查")
                return

            last_trade_date_str = latest_quote.get("trade_date")
            if not last_trade_date_str:
                return

            # 支持 YYYY-MM-DD 格式
            try:
                if "-" in last_trade_date_str:
                    last_trade_date = datetime.strptime(last_trade_date_str, "%Y-%m-%d").date()
                else:
                    last_trade_date = datetime.strptime(last_trade_date_str, "%Y%m%d").date()
            except ValueError:
                logger.warning(f"无法解析日期格式: {last_trade_date_str}")
                return

            today = date_type.today()

            # 计算缺失的交易日
            days_diff = (today - last_trade_date).days

            # 如果差异超过1天（允许当天），需要补录
            if days_diff > 1:
                # 获取股票列表（限制数量，避免补录时间过长）
                assert self.stock_info_repo is not None, "stock_info_repo not initialized"
                stocks = await self.stock_info_repo.get_by_market(MarketType.A_STOCK, limit=500)
                symbols = [s["symbol"] for s in stocks]

                if symbols:
                    # 计算补录日期范围
                    start_date = (last_trade_date + timedelta(days=1)).strftime("%Y%m%d")
                    end_date = today.strftime("%Y%m%d")

                    logger.info(
                        f"  📈 A股日线数据缺失 {days_diff} 天，触发补录 ({start_date} ~ {end_date})"
                    )

                    sync_result = await self.data_sync_service.sync_daily_quotes(
                        symbols=symbols,
                        start_date=start_date,
                        end_date=end_date,
                        source_id="tushare",
                    )

                    result["tasks_triggered"].append(
                        {
                            "task": "catchup_daily_quotes",
                            "status": sync_result["status"],
                            "records": sync_result.get("result", {}).get("total_quotes", 0),
                            "reason": f"缺失{days_diff}天数据",
                            "date_range": f"{start_date}~{end_date}",
                        }
                    )

                    logger.info(
                        f"  ✅ A股日线数据补录完成: "
                        f"{sync_result.get('result', {}).get('total_quotes', 0)} 条"
                    )
            else:
                logger.info("  ✅ A股日线数据最新")

        except Exception as e:
            logger.error(f"  ❌ A股日线数据检查失败: {e}")

    async def _check_and_catchup_company_info(self, result: Dict[str, Any]) -> None:
        """检查并补录A股公司信息"""
        try:
            # 获取最新的公司信息更新时间
            assert self.stock_company_repo is not None, "stock_company_repo not initialized"
            latest_companies = await self.stock_company_repo.find_many(
                {}, sort=[("updated_at", -1)], limit=1
            )
            latest_company = latest_companies[0] if latest_companies else None

            if not latest_company:
                logger.info("  ℹ️ 未找到公司信息，跳过公司信息补录检查")
                return

            last_update = latest_company.get("updated_at")
            if not last_update:
                return

            # 计算距离上次更新的天数
            days_since_update = (datetime.now() - last_update).days

            # 如果超过7天未更新，触发更新
            if days_since_update > 7:
                logger.info(f"  🏢 A股公司信息超过 {days_since_update} 天未更新，触发补录")

                # 获取股票列表（限制数量）
                assert self.stock_info_repo is not None, "stock_info_repo not initialized"
                stocks = await self.stock_info_repo.get_by_market(MarketType.A_STOCK, limit=100)
                symbols = [s["symbol"] for s in stocks]

                if symbols:
                    sync_result = await self.data_sync_service.sync_company_info(
                        symbols=symbols, source_id="tushare"
                    )

                    result["tasks_triggered"].append(
                        {
                            "task": "catchup_company_info",
                            "status": sync_result["status"],
                            "records": sync_result.get("result", {}).get("total_records", 0),
                            "reason": f"超过{days_since_update}天未更新",
                        }
                    )

                    logger.info(
                        f"  ✅ A股公司信息补录完成: "
                        f"{sync_result.get('result', {}).get('total_records', 0)} 条"
                    )
            else:
                logger.info(f"  ✅ A股公司信息最新，距上次更新 {days_since_update} 天")

        except Exception as e:
            logger.error(f"  ❌ A股公司信息检查失败: {e}")

    async def _check_and_catchup_financials(self, result: Dict[str, Any]) -> None:
        """检查并补录A股财务数据"""
        try:
            # 获取最新的财务数据报告期
            assert self.stock_financial_repo is not None, "stock_financial_repo not initialized"
            financials = await self.stock_financial_repo.find_many(
                {}, sort=[("report_date", -1)], limit=1
            )
            latest_financial = financials[0] if financials else None

            if not latest_financial:
                logger.info("  ℹ️ 未找到财务数据，跳过财务数据补录检查")
                return

            last_report_date_str = latest_financial.get("report_date")
            if not last_report_date_str:
                return

            last_report_date = datetime.strptime(last_report_date_str, "%Y%m%d")
            days_since_report = (datetime.now() - last_report_date).days

            # 如果超过30天未更新财务数据，触发更新
            if days_since_report > 30:
                logger.info(f"  💰 A股财务数据超过 {days_since_report} 天未更新，触发补录")

                # 获取股票列表（限制数量）
                assert self.stock_info_repo is not None, "stock_info_repo not initialized"
                stocks = await self.stock_info_repo.get_by_market(MarketType.A_STOCK, limit=50)
                symbols = [s["symbol"] for s in stocks]

                if symbols:
                    sync_result = await self.data_sync_service.sync_financials_with_fallback(
                        symbols=symbols
                    )

                    total_records = sync_result.get("result", {}).get("financials", {}).get(
                        "upserted", 0
                    ) + sync_result.get("result", {}).get("indicators", {}).get("upserted", 0)

                    result["tasks_triggered"].append(
                        {
                            "task": "catchup_financials",
                            "status": sync_result["status"],
                            "records": total_records,
                            "reason": f"超过{days_since_report}天未更新",
                        }
                    )

                    logger.info(f"  ✅ A股财务数据补录完成: {total_records} 条")
            else:
                logger.info(f"  ✅ A股财务数据最新，距上次报告 {days_since_report} 天")

        except Exception as e:
            logger.error(f"  ❌ A股财务数据检查失败: {e}")

    async def _initialize_data_source_status(self, result: Dict[str, Any]) -> None:
        """
        初始化数据源状态记录

        为所有配置的数据源创建初始状态记录，确保数据源状态监控页面能正常显示。
        只有当状态记录不存在时才会创建，避免覆盖已有状态。
        注意：健康检查被移至后台异步执行，不阻塞启动流程。
        """
        try:
            logger.info("🔍 初始化数据源状态记录...")

            # 延迟加载 repository
            from core.market_data.repositories.datasource import (
                DataSourceStatusRepository,
                SystemDataSourceRepository,
            )

            status_repo = DataSourceStatusRepository()
            system_source_repo = SystemDataSourceRepository()

            # 定义数据源配置映射（与 data_source_status.py 中的配置保持一致）
            # 简化并合并数据类型
            data_source_configs = {
                "A_STOCK": {
                    "stock_list": ["tushare", "akshare"],  # 股票列表
                    "daily_quotes": ["tushare", "akshare"],  # 日线行情
                    "minute_quotes": ["akshare"],  # 分钟K线
                    "financials": [
                        "tushare",
                        "akshare",
                    ],  # 财务数据 (包含 financials, financial_indicator)
                    "financial_indicator": ["akshare"],  # 财务指标数据
                    "company_info": ["tushare", "akshare"],  # 公司信息
                    "share_holders": ["tushare", "akshare"],  # 股东人数
                    "top_holders": ["akshare"],  # 十大股东
                    "stock_pledge": ["tushare"],  # 股权质押
                    "stock_repurchase": ["tushare"],  # 股票回购
                    "adjust_factor": ["tushare"],  # 复权因子
                    "sector": ["akshare"],  # 板块数据 (包含 index, sector)
                    "macro_economy": ["akshare", "tushare"],  # 宏观经济
                },
                "US_STOCK": {
                    "daily_quotes": ["yahoo", "alpha_vantage"],
                    "minute_quotes": ["yahoo"],
                    "financials": ["yahoo", "alpha_vantage"],
                    "company_info": ["yahoo"],
                    "index": ["yahoo"],
                },
                "HK_STOCK": {
                    "daily_quotes": ["yahoo", "akshare"],
                    "minute_quotes": ["yahoo"],
                    "financials": ["akshare"],
                    "company_info": ["yahoo"],
                },
            }

            initialized_count = 0
            skipped_count = 0
            health_check_tasks = []  # 收集需要执行健康检查的任务

            # 遍历所有市场和数据类型
            for market, data_types in data_source_configs.items():
                for data_type, source_ids in data_types.items():
                    for source_id in source_ids:
                        try:
                            # 检查状态记录是否已存在
                            existing_status = await status_repo.get_status(
                                market=market,
                                data_type=data_type,
                                source_type=DataSourceType.SYSTEM,
                                source_id=source_id,
                            )

                            if existing_status:
                                skipped_count += 1
                                continue

                            # 获取数据源配置，判断是否可用
                            source_config = await system_source_repo.get_config(source_id, market)
                            config = source_config.get("config", {}) if source_config else {}

                            # 根据数据源类型和配置确定初始状态
                            is_available = False
                            if source_id == "tushare":
                                # TuShare 需要 API Token
                                is_available = bool(config.get("api_token"))
                            elif source_id == "alpha_vantage":
                                # Alpha Vantage 需要 API Key
                                is_available = bool(config.get("api_key"))
                            else:
                                # 其他数据源（AkShare, Yahoo）默认可用
                                is_available = True

                            # 创建初始状态记录
                            initial_status = DataSourceHealthStatus(
                                market=market,
                                data_type=data_type,
                                source_type=DataSourceType.SYSTEM,
                                source_id=source_id,
                                user_id=None,
                                status=(
                                    DataSourceStatus.HEALTHY
                                    if is_available
                                    else DataSourceStatus.UNAVAILABLE
                                ),
                                last_check_type="initialization",
                                response_time_ms=None,
                                avg_response_time_ms=None,
                                failure_count=0,
                                last_error=({"note": "未配置凭证"} if not is_available else None),
                                is_fallback=False,
                                fallback_info=None,
                                api_endpoints=None,
                            )

                            await status_repo.upsert_status(initial_status)
                            initialized_count += 1
                            logger.debug(
                                f"  初始化数据源状态: "
                                f"{market}/{data_type}/{source_id} -> "
                                f"{initial_status.status} (可用: {is_available})"
                            )

                            # 收集需要执行健康检查的数据源（跳过已知不可用的）
                            if is_available:
                                health_check_tasks.append(
                                    {
                                        "market": market,
                                        "data_type": data_type,
                                        "source_id": source_id,
                                    }
                                )

                        except Exception as e:
                            logger.warning(
                                f"  ⚠️ 初始化数据源状态失败 {market}/{data_type}/{source_id}: {e}"
                            )

            result["tasks_triggered"].append(
                {
                    "task": "initialize_data_source_status",
                    "status": "success",
                    "records": initialized_count,
                    "skipped": skipped_count,
                }
            )

            logger.info(
                f"  ✅ 数据源状态初始化完成: 新增 {initialized_count} 条，跳过 {skipped_count} 条"
            )
            logger.info(f"  ℹ️ 健康检查将在后台异步执行，共 {len(health_check_tasks)} 个检查项")

            # 将健康检查任务添加到结果中，供调用者启动后台任务
            result["health_check_tasks"] = health_check_tasks

        except Exception as e:
            logger.error(f"  ❌ 数据源状态初始化失败: {e}")
            result["tasks_triggered"].append(
                {"task": "initialize_data_source_status", "status": "failed", "error": str(e)}
            )

    async def run_health_checks_parallel(
        self, health_check_tasks: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        并行执行数据源健康检查

        Args:
            health_check_tasks: 健康检查任务列表，每个任务包含 market, data_type, source_id

        Returns:
            健康检查结果汇总
        """
        import asyncio

        logger.info("=" * 60)
        logger.info("📊 数据源健康检查开始")
        logger.info(f"📋 共 {len(health_check_tasks)} 个检查项")
        logger.info("=" * 60)

        monitor_service = self.data_sync_service._get_monitor_service()
        total = len(health_check_tasks)
        completed = 0

        async def check_single(task: Dict[str, str]) -> Dict[str, Any]:
            """执行单个健康检查"""
            nonlocal completed

            market = task["market"]
            data_type = task["data_type"]
            source_id = task["source_id"]

            try:
                logger.info(
                    f"  🔍 [{completed + 1}/{total}] 检查 {market}/{data_type}/{source_id}..."
                )
                result = await monitor_service.check_single_source(
                    source_id=source_id,
                    market=market,
                    data_type=data_type,
                    check_type="initialization",
                )

                completed += 1
                status_icon = "✅" if result.get("status") == "healthy" else "❌"
                logger.info(
                    f"  {status_icon} [{completed}/{total}] {market}/{data_type}/{source_id} - "
                    f"{result.get('status', 'unknown')} ({result.get('response_time_ms', 0)}ms)"
                )

                return {
                    "success": result.get("status") == "healthy",
                    "market": market,
                    "data_type": data_type,
                    "source_id": source_id,
                    "status": result.get("status"),
                    "response_time_ms": result.get("response_time_ms", 0),
                }
            except Exception as e:
                completed += 1
                logger.warning(
                    f"  ⚠️ [{completed}/{total}] {market}/{data_type}/{source_id} - 失败: {e}"
                )
                return {
                    "success": False,
                    "market": market,
                    "data_type": data_type,
                    "source_id": source_id,
                    "error": str(e),
                }

        # 并行执行所有健康检查
        results = await asyncio.gather(
            *[check_single(task) for task in health_check_tasks], return_exceptions=True
        )

        # 统计结果
        passed = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = sum(1 for r in results if isinstance(r, dict) and not r.get("success"))
        errors = sum(1 for r in results if isinstance(r, Exception))

        logger.info("=" * 60)
        logger.info(f"✅ 健康检查完成: 通过 {passed} 个，失败 {failed} 个，异常 {errors} 个")
        logger.info("=" * 60)

        return {
            "total": len(health_check_tasks),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "results": results,
        }
