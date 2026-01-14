"""
数据源状态监控服务

负责监控数据源的健康状态、执行健康检查、自动降级和恢复。
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio

from core.market_data.models.datasource import (
    DataSourceStatus,
    DataSourceType,
    DataSourceHealthStatus,
    DataSourceStatusHistory,
)
from core.market_data.repositories.datasource import (
    SystemDataSourceRepository,
    DataSourceStatusRepository,
    DataSourceStatusHistoryRepository,
)
from core.market_data.sources.a_stock.tushare_adapter import TuShareAdapter
from core.market_data.sources.a_stock.akshare_adapter import AkShareAdapter

logger = logging.getLogger(__name__)


class SourceMonitorService:
    """数据源状态监控服务"""

    def __init__(self):
        self.system_source_repo = SystemDataSourceRepository()
        self.status_repo = DataSourceStatusRepository()
        self.status_history_repo = DataSourceStatusHistoryRepository()

        self._adapters: Dict[str, Any] = {}
        self._check_interval = 300

    def _get_adapter(self, source_id: str, config: Dict[str, Any]) -> Any:
        """
        获取数据源适配器实例

        Args:
            source_id: 数据源ID
            config: 配置信息

        Returns:
            适配器实例
        """
        if source_id not in self._adapters:
            if source_id == "tushare":
                self._adapters[source_id] = TuShareAdapter(config)
            elif source_id == "akshare":
                self._adapters[source_id] = AkShareAdapter(config)
            else:
                raise ValueError(f"Unsupported data source: {source_id}")

        return self._adapters[source_id]

    async def _check_api_health(
        self,
        source_id: str,
        market: str,
        data_type: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        检查API健康状态

        Args:
            source_id: 数据源ID
            market: 市场类型
            data_type: 数据类型
            config: 配置信息

        Returns:
            健康检查结果
        """
        start_time = datetime.now()

        try:
            adapter = self._get_adapter(source_id, config)

            if data_type == "stock_list":
                result = await adapter.get_stock_list(MarketType.A_STOCK)
                success = len(result) > 0
            elif data_type == "daily_quotes":
                result = await adapter.get_daily_quotes("000001.SZ", start_date="20240101", end_date="20240105")
                success = len(result) > 0
            elif data_type == "financials":
                result = await adapter.get_stock_financials("000001.SZ")
                success = len(result) > 0
            elif data_type == "financial_indicator":
                result = await adapter.get_financial_indicators("000001.SZ")
                success = len(result) > 0
            elif data_type == "company_info":
                result = await adapter.get_stock_company("000001.SZ")
                success = result is not None
            elif data_type == "shibor":
                result = await adapter.get_shibor()
                success = len(result) > 0
            else:
                success = True

            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return {
                "success": success,
                "response_time_ms": response_time_ms,
                "error": None
            }

        except Exception as e:
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Health check failed for {source_id}/{data_type}: {e}")

            return {
                "success": False,
                "response_time_ms": response_time_ms,
                "error": {
                    "code": type(e).__name__,
                    "message": str(e)
                }
            }

    async def check_single_source(
        self,
        source_id: str,
        market: str,
        data_type: str,
        check_type: str = "manual_check"
    ) -> Dict[str, Any]:
        """
        检查单个数据源的状态

        Args:
            source_id: 数据源ID
            market: 市场类型
            data_type: 数据类型
            check_type: 检查类型

        Returns:
            检查结果
        """
        config = await self.system_source_repo.get_config(source_id, market)
        if not config:
            return {
                "success": False,
                "error": "Config not found"
            }

        check_result = await self._check_api_health(
            source_id=source_id,
            market=market,
            data_type=data_type,
            config=config["config"]
        )

        existing_status = await self.status_repo.get_status(
            market=market,
            data_type=data_type,
            source_type=DataSourceType.SYSTEM,
            source_id=source_id
        )

        new_status = DataSourceStatus.HEALTHY if check_result["success"] else DataSourceStatus.UNAVAILABLE

        await self.status_repo.update_status(
            market=market,
            data_type=data_type,
            source_type=DataSourceType.SYSTEM,
            source_id=source_id,
            status=new_status,
            response_time_ms=check_result["response_time_ms"],
            error=check_result["error"],
            check_type=check_type
        )

        if existing_status and existing_status["status"] != new_status.value:
            history = DataSourceStatusHistory(
                market=market,
                data_type=data_type,
                source_type=DataSourceType.SYSTEM,
                source_id=source_id,
                event_type="status_changed",
                from_status=existing_status["status"],
                to_status=new_status.value,
                response_time_ms=check_result["response_time_ms"],
                check_type=check_type
            )
            await self.status_history_repo.record_event(history)
            logger.info(f"Source {source_id}/{data_type} status changed: {existing_status['status']} -> {new_status.value}")

        return {
            "source_id": source_id,
            "market": market,
            "data_type": data_type,
            "status": new_status.value,
            "response_time_ms": check_result["response_time_ms"],
            "error": check_result["error"]
        }

    async def check_all_sources(
        self,
        market: Optional[str] = None,
        check_type: str = "scheduled"
    ) -> Dict[str, Any]:
        """
        检查所有数据源的状态

        Args:
            market: 市场类型（可选）
            check_type: 检查类型

        Returns:
            检查结果汇总
        """
        configs = await self.system_source_repo.get_enabled_configs(market or "A_STOCK")

        results = []
        for config in configs:
            source_id = config["source_id"]
            market = config["market"]

            data_types = config.get("supported_data_types", [
                "stock_list", "daily_quotes", "financials", "financial_indicator", "company_info"
            ])

            for data_type in data_types:
                try:
                    result = await self.check_single_source(
                        source_id=source_id,
                        market=market,
                        data_type=data_type,
                        check_type=check_type
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to check {source_id}/{data_type}: {e}")

        summary = await self.status_repo.get_status_summary(market)

        return {
            "check_type": check_type,
            "timestamp": datetime.now().isoformat(),
            "total_checks": len(results),
            "results": results,
            "summary": summary
        }

    async def handle_failure(
        self,
        market: str,
        data_type: str,
        source_id: str,
        error: Dict[str, Any],
        check_type: str = "sync_task"
    ) -> Dict[str, Any]:
        """
        处理数据源失败

        Args:
            market: 市场类型
            data_type: 数据类型
            source_id: 数据源ID
            error: 错误信息
            check_type: 检查类型

        Returns:
            处理结果
        """
        status = await self.status_repo.get_status(
            market=market,
            data_type=data_type,
            source_type=DataSourceType.SYSTEM,
            source_id=source_id
        )

        if not status:
            await self.status_repo.update_status(
                market=market,
                data_type=data_type,
                source_type=DataSourceType.SYSTEM,
                source_id=source_id,
                status=DataSourceStatus.UNAVAILABLE,
                error=error,
                check_type=check_type
            )
            return {"action": "created_unavailable"}

        current_status = status["status"]
        failure_count = status.get("failure_count", 0) + 1
        max_failure_count = status.get("max_failure_count", 3)

        if failure_count >= max_failure_count:
            new_status = DataSourceStatus.UNAVAILABLE

            history = DataSourceStatusHistory(
                market=market,
                data_type=data_type,
                source_type=DataSourceType.SYSTEM,
                source_id=source_id,
                event_type="status_changed",
                from_status=current_status,
                to_status=new_status.value,
                error_code=error.get("code"),
                error_message=error.get("message"),
                check_type=check_type
            )
            await self.status_history_repo.record_event(history)

            await self.status_repo.update_status(
                market=market,
                data_type=data_type,
                source_type=DataSourceType.SYSTEM,
                source_id=source_id,
                status=new_status,
                error=error,
                check_type=check_type
            )

            logger.warning(f"Source {source_id}/{data_type} marked as unavailable after {failure_count} failures")

            return {"action": "marked_unavailable", "failure_count": failure_count}
        else:
            await self.status_repo.increment_failure_count(
                market=market,
                data_type=data_type,
                source_type=DataSourceType.SYSTEM,
                source_id=source_id,
                error=error
            )

            return {"action": "incremented_failure", "failure_count": failure_count}

    async def handle_recovery(
        self,
        market: str,
        data_type: str,
        source_id: str,
        response_time_ms: int
    ) -> Dict[str, Any]:
        """
        处理数据源恢复

        Args:
            market: 市场类型
            data_type: 数据类型
            source_id: 数据源ID
            response_time_ms: 响应时间

        Returns:
            处理结果
        """
        status = await self.status_repo.get_status(
            market=market,
            data_type=data_type,
            source_type=DataSourceType.SYSTEM,
            source_id=source_id
        )

        if not status or status["status"] == DataSourceStatus.HEALTHY.value:
            return {"action": "already_healthy"}

        previous_status = status["status"]

        await self.status_repo.reset_failure_count(
            market=market,
            data_type=data_type,
            source_type=DataSourceType.SYSTEM,
            source_id=source_id
        )

        await self.status_repo.update_status(
            market=market,
            data_type=data_type,
            source_type=DataSourceType.SYSTEM,
            source_id=source_id,
            status=DataSourceStatus.HEALTHY,
            response_time_ms=response_time_ms
        )

        history = DataSourceStatusHistory(
            market=market,
            data_type=data_type,
            source_type=DataSourceType.SYSTEM,
            source_id=source_id,
            event_type="recovered",
            from_status=previous_status,
            to_status=DataSourceStatus.HEALTHY.value,
            response_time_ms=response_time_ms
        )
        await self.status_history_repo.record_event(history)

        logger.info(f"Source {source_id}/{data_type} recovered from {previous_status}")

        return {"action": "recovered", "previous_status": previous_status}

    async def get_status_summary(
        self,
        market: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取状态汇总

        Args:
            market: 市场类型（可选）

        Returns:
            状态汇总
        """
        summary = await self.status_repo.get_status_summary(market)

        all_status = await self.status_repo.get_all_status(market)

        healthy = [s for s in all_status if s["status"] == DataSourceStatus.HEALTHY.value]
        degraded = [s for s in all_status if s["status"] == DataSourceStatus.DEGRADED.value]
        unavailable = [s for s in all_status if s["status"] == DataSourceStatus.UNAVAILABLE.value]

        return {
            "market": market or "ALL",
            "timestamp": datetime.now().isoformat(),
            "counts": summary,
            "details": {
                "healthy": len(healthy),
                "degraded": len(degraded),
                "unavailable": len(unavailable)
            },
            "sources": {
                "healthy": healthy,
                "degraded": degraded,
                "unavailable": unavailable
            }
        }

    async def get_source_status(
        self,
        source_id: str,
        market: str
    ) -> List[Dict[str, Any]]:
        """
        获取指定数据源的所有状态

        Args:
            source_id: 数据源ID
            market: 市场类型

        Returns:
            状态列表
        """
        all_status = await self.status_repo.get_all_status(market)
        return [s for s in all_status if s["source_id"] == source_id]

    async def get_recent_events(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取最近的事件记录

        Args:
            hours: 时间范围（小时）
            limit: 返回数量限制

        Returns:
            事件列表
        """
        return await self.status_history_repo.get_recent_failures(hours, limit)

    async def get_source_history(
        self,
        source_id: str,
        event_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取指定数据源的历史记录

        Args:
            source_id: 数据源ID
            event_type: 事件类型（可选）
            limit: 返回数量限制

        Returns:
            历史记录列表
        """
        return await self.status_history_repo.get_source_history(source_id, event_type, limit)

    async def get_error_statistics(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        获取错误统计

        Args:
            hours: 时间范围（小时）

        Returns:
            错误统计
        """
        return await self.status_history_repo.get_error_statistics(hours=hours)

    async def auto_monitor_loop(self):
        """
        自动监控循环

        定期检查所有数据源的健康状态
        """
        logger.info("Starting source monitor loop")

        while True:
            try:
                logger.info("Running scheduled health check")
                result = await self.check_all_sources(check_type="scheduled")

                # 检查是否有不健康的数据源，触发告警
                await self._check_and_alert(result)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")

            await asyncio.sleep(self._check_interval)

    async def _check_and_alert(self, check_result: Dict[str, Any]) -> None:
        """
        检查健康检查结果并触发告警

        Args:
            check_result: 健康检查结果
        """
        try:
            results = check_result.get("results", [])
            unavailable_sources = [
                r for r in results
                if r.get("status") == DataSourceStatus.UNAVAILABLE.value
            ]

            if unavailable_sources:
                await self._send_alert(
                    alert_type="source_unavailable",
                    message=f"{len(unavailable_sources)} 个数据源不可用",
                    details=unavailable_sources
                )

        except Exception as e:
            logger.error(f"Failed to check and alert: {e}")

    async def _send_alert(
        self,
        alert_type: str,
        message: str,
        details: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        发送告警通知

        Args:
            alert_type: 告警类型
            message: 告警消息
            details: 详细信息
        """
        # 记录告警日志
        logger.warning(f"ALERT [{alert_type}]: {message}")

        if details:
            for detail in details:
                logger.warning(f"  - {detail.get('source_id')}/{detail.get('data_type')}: {detail.get('error')}")

        # TODO: 集成外部告警系统（如钉钉、企业微信、邮件等）
        # 可以通过配置文件或环境变量配置告警渠道
        # await self._send_dingtalk_alert(message, details)
        # await self._send_email_alert(message, details)

    def set_check_interval(self, interval_seconds: int) -> None:
        """
        设置健康检查间隔

        Args:
            interval_seconds: 检查间隔（秒）
        """
        self._check_interval = interval_seconds
        logger.info(f"Health check interval set to {interval_seconds} seconds")

    async def start_monitoring(self):
        """启动监控"""
        asyncio.create_task(self.auto_monitor_loop())

    async def stop_monitoring(self):
        """停止监控"""
        pass

    from core.market_data.models import MarketType
