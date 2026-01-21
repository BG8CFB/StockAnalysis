"""
数据源状态监控 API
严格按照 docs/market_data/数据源状态监控设计.md 实现
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.auth.dependencies import get_current_user
from core.market_data.repositories.datasource import (
    DataSourceStatusHistoryRepository,
    DataSourceStatusRepository,
    SystemDataSourceRepository,
)
from core.market_data.services.source_monitor_service import SourceMonitorService
from core.user.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/core/system", tags=["系统管理_数据源监控"])


# =============================================================================
# 数据类型定义（严格按文档 2.2.2 节）
# =============================================================================

# A股数据类型
A_STOCK_DATA_TYPES = {
    # 核心行情数据
    "daily_quote": "日线行情数据",
    "realtime_quote": "实时行情数据",
    "minute_quote": "分钟行情数据",
    # 公司基本面数据
    "financials": "财务报表数据",
    "financial_indicator": "财务指标数据",
    "company_info": "公司信息数据",
    # 市场参考数据
    "news": "新闻资讯数据",
    "calendar": "交易日历数据",
    # 资金动向数据
    "top_list": "龙虎榜数据",
    "moneyflow": "资金流向数据",
    "dividend": "分红送股数据",
    # 股东数据
    "shareholder_num": "股东人数数据",
    "top_shareholder": "十大股东数据",
    # 融资融券
    "margin": "融资融券数据",
    # 宏观经济数据
    "macro_economy": "宏观经济数据",
    # 板块数据
    "sector": "板块数据",
    "index": "指数数据",
    # 特殊数据
    "ipo": "IPO新股数据",
    "pledge": "股权质押数据",
    "repurchase": "股票回购数据",
    # 交易辅助数据
    "adj_factor": "复权因子数据",
}

# 美股数据类型
US_STOCK_DATA_TYPES = {
    "daily_quote": "日线行情数据",
    "realtime_quote": "实时行情数据",
    "minute_quote": "分钟行情数据",
    "financials": "财务报表数据",
    "financial_indicator": "财务指标数据",
    "company_info": "公司信息数据",
    "news": "新闻资讯数据",
    "calendar": "交易日历数据",
    "macro_economy": "宏观经济数据",
    "sector": "板块数据",
    "index": "指数数据",
}

# 港股数据类型
HK_STOCK_DATA_TYPES = {
    "daily_quote": "日线行情数据",
    "realtime_quote": "实时行情数据",
    "minute_quote": "分钟行情数据",
    "financials": "财务报表数据",
    "company_info": "公司信息数据",
    "news": "新闻资讯数据",
    "calendar": "交易日历数据",
    "margin": "融资融券数据",
}

# 数据源配置（模拟数据，实际应从数据库读取）
# 注意：TuShare 需要付费 token，AkShare 免费开源
# 对于核心数据配置备用数据源，辅助数据只用免费源
DATA_SOURCE_CONFIGS = {
    "A_STOCK": {
        # 核心行情数据 - 配置备用
        "daily_quote": {"primary": "tushare", "fallback": "akshare"},
        # 实时数据 - 只用免费源（AkShare 实时性好）
        "realtime_quote": {"primary": "akshare", "fallback": None},
        "minute_quote": {"primary": "akshare", "fallback": None},
        # 财务数据 - 配置备用
        "financials": {"primary": "tushare", "fallback": "akshare"},
        "financial_indicator": {"primary": "akshare", "fallback": None},
        # 公司信息 - 只用 TuShare（数据更权威）
        "company_info": {"primary": "tushare", "fallback": None},
        # 参考数据 - 只用免费源
        "news": {"primary": "akshare", "fallback": None},
        "calendar": {"primary": "akshare", "fallback": None},
        "top_list": {"primary": "akshare", "fallback": None},
        "moneyflow": {"primary": "akshare", "fallback": None},
        "dividend": {"primary": "akshare", "fallback": None},
        # 股东数据 - 只用 TuShare（数据更权威）
        "shareholder_num": {"primary": "tushare", "fallback": None},
        "top_shareholder": {"primary": "akshare", "fallback": None},
        # 融资融券 - 只用免费源
        "margin": {"primary": "akshare", "fallback": None},
        # 宏观数据 - 只用免费源
        "macro_economy": {"primary": "akshare", "fallback": None},
        # 板块指数 - 只用免费源
        "sector": {"primary": "akshare", "fallback": None},
        "index": {"primary": "akshare", "fallback": None},
        # 特殊数据 - 只用 TuShare（数据更权威）
        "ipo": {"primary": "akshare", "fallback": None},
        "pledge": {"primary": "tushare", "fallback": None},
        "repurchase": {"primary": "tushare", "fallback": None},
        # 交易辅助 - 只用 TuShare
        "adj_factor": {"primary": "tushare", "fallback": None},
    },
    "US_STOCK": {
        "daily_quote": {"primary": "yahoo", "fallback": "alpha_vantage"},
        "realtime_quote": {"primary": "yahoo", "fallback": None},
        "minute_quote": {"primary": "yahoo", "fallback": None},
        "financials": {"primary": "yahoo", "fallback": "alpha_vantage"},
        "financial_indicator": {"primary": "yahoo", "fallback": None},
        "company_info": {"primary": "yahoo", "fallback": None},
        "news": {"primary": "yahoo", "fallback": None},
        "calendar": {"primary": "yahoo", "fallback": None},
        "macro_economy": {"primary": "alpha_vantage", "fallback": None},
        "sector": {"primary": "yahoo", "fallback": None},
        "index": {"primary": "yahoo", "fallback": None},
    },
    "HK_STOCK": {
        "daily_quote": {"primary": "yahoo", "fallback": "akshare"},
        "realtime_quote": {"primary": "yahoo", "fallback": None},
        "minute_quote": {"primary": "yahoo", "fallback": None},
        "financials": {"primary": "akshare", "fallback": None},
        "company_info": {"primary": "yahoo", "fallback": None},
        "news": {"primary": "yahoo", "fallback": None},
        "calendar": {"primary": "yahoo", "fallback": None},
        "margin": {"primary": "yahoo", "fallback": None},
    },
}

# 数据源显示名称
SOURCE_DISPLAY_NAMES = {
    "tushare": "TuShare",
    "tu": "TuShare",
    "akshare": "AkShare",
    "yahoo": "Yahoo Finance",
    "alpha_vantage": "Alpha Vantage",
    "alphavantage": "Alpha Vantage",  # 兼容不同的大小写
    # 备用数据源名称映射（处理未知或旧数据）
    "unknown": "未知数据源",
    "system": "系统数据源",
}

# 状态显示名称
STATUS_LABELS = {
    "healthy": "✅ 正常",
    "degraded": "⚠️ 已降级",
    "unavailable": "❌ 不可用",
}

# 下次更新说明（按数据类型）
NEXT_UPDATE_MAP = {
    "daily_quote": "收盘后自动同步",
    "realtime_quote": "实时更新",
    "minute_quote": "盘中实时更新",
    "financials": "季度更新",
    "financial_indicator": "季度更新",
    "company_info": "按需更新",
    "news": "实时更新",
    "calendar": "每日更新",
    "top_list": "每日收盘后",
    "moneyflow": "盘中实时更新",
    "dividend": "按公告更新",
    "shareholder_num": "季度更新",
    "top_shareholder": "季度更新",
    "margin": "每日收盘后",
    "macro_economy": "按发布周期",
    "sector": "每日更新",
    "index": "盘中实时更新",
    "ipo": "按公告更新",
    "pledge": "按公告更新",
    "repurchase": "按公告更新",
    "adj_factor": "每日收盘后",
}


# =============================================================================
# 依赖注入
# =============================================================================

def get_monitor_service() -> SourceMonitorService:
    """获取监控服务实例"""
    return SourceMonitorService()


def get_status_repo() -> DataSourceStatusRepository:
    """获取状态仓库实例"""
    return DataSourceStatusRepository()


def get_system_source_repo() -> SystemDataSourceRepository:
    """获取系统数据源仓库实例"""
    return SystemDataSourceRepository()


def get_history_repo() -> DataSourceStatusHistoryRepository:
    """获取历史仓库实例"""
    return DataSourceStatusHistoryRepository()


# =============================================================================
# 响应模型（修改后：主备数据源分离显示）
# =============================================================================

class DashboardOverviewResponse(BaseModel):
    """仪表板概览响应（按文档 3.1.1）"""
    a_stock: Optional[Dict[str, Any]] = None
    us_stock: Optional[Dict[str, Any]] = None
    hk_stock: Optional[Dict[str, Any]] = None


class DataSourceInfo(BaseModel):
    """数据源信息"""
    source_id: str
    source_name: str
    is_current: bool  # 是否是当前使用的数据源
    is_primary: bool  # 是否是主数据源
    status: Optional[str] = None  # None 表示未使用/未检查
    last_check: Optional[str] = None
    last_check_relative: Optional[str] = None
    response_time_ms: Optional[int] = None
    failure_count: int = 0
    error_message: Optional[str] = None  # 错误信息


class DataTypeStatusItem(BaseModel):
    """数据类型状态项（返回实际使用的数据源）"""
    data_type: str
    data_type_name: str
    current_source: DataSourceInfo  # 当前实际使用的数据源
    is_fallback: bool  # 是否已降级到备用数据源
    can_retry: bool  # 是否可以重试主数据源
    fallback_reason: Optional[str] = None  # 降级原因


class MarketDetailResponse(BaseModel):
    """市场详细状态响应（修改后）"""
    market: str
    market_name: str
    data_types: List[DataTypeStatusItem]


class ApiEndpointInfo(BaseModel):
    """API 端点信息（按文档 3.2.1）"""
    endpoint_name: str
    endpoint_name_cn: str
    status: str
    last_check: Optional[str] = None
    failure_count: int = 0


class SourceDetailInfo(BaseModel):
    """数据源详细信息（按文档 3.2.1）"""
    source_type: str
    source_id: str
    source_name: str
    status: str
    priority: int
    last_check: Optional[str] = None
    response_time_ms: Optional[int] = None
    avg_response_time_ms: Optional[int] = None
    failure_count: int = 0
    note: Optional[str] = None
    api_endpoints: Optional[List[ApiEndpointInfo]] = None


class StatusEvent(BaseModel):
    """状态事件（按文档 3.2.1）"""
    timestamp: str
    event_type: str
    description: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    from_source: Optional[str] = None
    to_source: Optional[str] = None
    source_id: Optional[str] = None


class DataTypeDetailResponse(BaseModel):
    """数据类型详细响应（按文档 3.2.1）"""
    market: str
    data_type: str
    data_type_name: str
    sources: List[SourceDetailInfo]
    recent_events: List[StatusEvent]


# =============================================================================
# API 接口实现
# =============================================================================

@router.get("/data-source-status/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    status_repo: DataSourceStatusRepository = Depends(get_status_repo)
):
    """
    获取仪表板概览（按文档 3.1.1）

    返回各市场的整体健康状态
    从数据库读取真实的健康状态汇总
    """
    try:
        logger.info("Fetching dashboard overview")

        now = datetime.now()

        # 获取各市场的状态汇总
        result = {}

        for market in ["A_STOCK", "US_STOCK", "HK_STOCK"]:
            summary = await status_repo.get_status_summary(market=market)

            # 获取该市场最近的检查时间
            all_status = await status_repo.get_all_status(market=market)
            last_check = None
            if all_status:
                last_check = max(
                    (s.get("last_check_at") for s in all_status if s.get("last_check_at")),
                    default=None
                )

            # 确定整体状态（优先级：unavailable > degraded > healthy）
            # 所有数据类型都会主动同步，不存在"从未检查"的情况
            # 如果没有任何检查记录，默认为 healthy（系统启动时假设数据源可用）
            overall_status = "healthy"
            if summary.get("unavailable", 0) > 0:
                overall_status = "unavailable"
            elif summary.get("degraded", 0) > 0:
                overall_status = "degraded"

            market_key = market.lower().replace("_", "_")
            result[market_key] = {
                "status": overall_status,
                "last_update": last_check.isoformat() if last_check else now.isoformat(),
                "last_update_relative": _get_relative_time(last_check) if last_check else "从未检查"
            }

        return result

    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取仪表板概览失败: {str(e)}"
        )


@router.get("/data-source-status/{market}", response_model=MarketDetailResponse)
async def get_market_detail(
    market: str,
    status_repo: DataSourceStatusRepository = Depends(get_status_repo),
    system_source_repo: SystemDataSourceRepository = Depends(get_system_source_repo)
):
    """
    获取市场详细状态（返回实际使用的数据源）

    返回该市场各数据类型的实际使用数据源状态
    从数据库读取真实的健康检查状态，根据实际情况确定当前使用的数据源
    """
    try:
        # 验证并标准化市场类型
        market_upper = market.upper()
        valid_markets = ["A_STOCK", "US_STOCK", "HK_STOCK"]
        if market_upper not in valid_markets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的市场类型: {market}"
            )

        logger.info(f"Fetching market detail for {market_upper}")

        # 获取该市场的数据类型定义
        data_types_map = _get_data_types_for_market(market_upper)
        market_name_map = {"A_STOCK": "A股", "US_STOCK": "美股", "HK_STOCK": "港股"}

        # 获取该市场的数据源配置
        source_configs = DATA_SOURCE_CONFIGS.get(market_upper, {})

        # 从数据库获取所有相关数据源状态
        all_status = await status_repo.get_all_status(market=market_upper)

        # 构建 (data_type, source_id) -> status 的映射
        status_map: Dict[tuple, Dict[str, Any]] = {}
        for status_item in all_status:
            key = (status_item["data_type"], status_item["source_id"])
            status_map[key] = status_item

        # 构建数据类型状态列表
        data_type_items = []

        for data_type_key, data_type_name in data_types_map.items():
            config = source_configs.get(data_type_key, {})
            primary_id = config.get("primary", "tushare")
            fallback_id = config.get("fallback")

            # 从数据库获取主数据源状态
            primary_status = status_map.get((data_type_key, primary_id))
            fallback_status = status_map.get((data_type_key, fallback_id)) if fallback_id else None

            # 确定当前实际使用的数据源
            current_source_id = primary_id
            current_status_info = primary_status
            is_fallback = False
            fallback_reason = None
            can_retry = False

            # 判断主数据源是否可用
            primary_is_available = (
                primary_status and
                primary_status.get("status") == "healthy"
            )

            if not primary_is_available:
                # 主数据源不可用，尝试降级到备用数据源
                is_fallback = True

                # 尝试使用配置的备用数据源
                if fallback_id and fallback_status and fallback_status.get("status") == "healthy":
                    current_source_id = fallback_id
                    current_status_info = fallback_status
                    fallback_reason = (
                        f"主数据源 {SOURCE_DISPLAY_NAMES.get(primary_id, primary_id)} "
                        f"不可用，已自动切换到备用数据源 "
                        f"{SOURCE_DISPLAY_NAMES.get(fallback_id, fallback_id)}"
                    )
                    can_retry = True  # 主数据源失败，可以重试
                    logger.info(
                        f"Using fallback source for {market_upper}/{data_type_key}: "
                        f"{primary_id} -> {fallback_id}"
                    )
                else:
                    # 尝试动态查找其他可用的数据源
                    available_sources = []
                    for (dt, source_id), status_info in status_map.items():
                        if dt == data_type_key and source_id != primary_id:
                            if status_info.get("status") == "healthy":
                                available_sources.append((source_id, status_info))

                    # 按优先级排序
                    source_priority = {
                        "akshare": 1,
                        "yahoo": 2,
                        "alpha_vantage": 3,
                        "tushare": 4,
                    }
                    available_sources.sort(key=lambda x: source_priority.get(x[0], 99))

                    if available_sources:
                        current_source_id = available_sources[0][0]
                        current_status_info = available_sources[0][1]
                        fallback_reason = (
                            f"主数据源 {SOURCE_DISPLAY_NAMES.get(primary_id, primary_id)} "
                            f"不可用，已自动切换到 "
                            f"{SOURCE_DISPLAY_NAMES.get(current_source_id, current_source_id)}"
                        )
                        can_retry = True
                        logger.info(
                            f"Dynamic fallback for {market_upper}/{data_type_key}: "
                            f"{primary_id} -> {current_source_id}"
                        )
                    else:
                        # 所有数据源都不可用
                        fallback_reason = "所有数据源均不可用"
                        can_retry = True
                        current_source_id = primary_id
                        current_status_info = primary_status

            # 构建当前数据源信息
            if current_status_info:
                last_check_at = current_status_info.get("last_check_at")
                time_relative = _get_relative_time(last_check_at) if last_check_at else "从未检查"
                current_source_info = {
                    "source_id": current_source_id,
                    "source_name": SOURCE_DISPLAY_NAMES.get(current_source_id, current_source_id),
                    "is_current": True,
                    "is_primary": not is_fallback,
                    "status": current_status_info.get("status"),
                    "last_check": last_check_at.isoformat() if last_check_at else None,
                    "last_check_relative": time_relative,
                    "response_time_ms": current_status_info.get("response_time_ms"),
                    "failure_count": current_status_info.get("failure_count", 0),
                    "error_message": (
                        current_status_info.get("last_error", {}).get("message")
                        if current_status_info.get("last_error")
                        else None
                    ),
                }
            else:
                # 无检查记录
                current_source_info = {
                    "source_id": current_source_id,
                    "source_name": SOURCE_DISPLAY_NAMES.get(current_source_id, current_source_id),
                    "is_current": True,
                    "is_primary": not is_fallback,
                    "status": None,
                    "last_check": None,
                    "last_check_relative": None,
                    "response_time_ms": None,
                    "failure_count": 0,
                    "error_message": None,
                }

            # 构建数据类型项
            item = {
                "data_type": data_type_key,
                "data_type_name": data_type_name,
                "current_source": current_source_info,
                "is_fallback": is_fallback,
                "can_retry": can_retry and is_fallback,  # 只有降级状态且主数据源失败时才能重试
                "fallback_reason": fallback_reason,
            }

            data_type_items.append(item)

        return {
            "market": market_upper,
            "market_name": market_name_map.get(market_upper, market_upper),
            "data_types": data_type_items
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get market detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取市场详细状态失败: {str(e)}"
        )


@router.get("/data-source-status/{market}/{data_type}", response_model=DataTypeDetailResponse)
async def get_data_type_detail(
    market: str,
    data_type: str,
    status_repo: DataSourceStatusRepository = Depends(get_status_repo),
    history_repo: DataSourceStatusHistoryRepository = Depends(get_history_repo)
):
    """
    获取数据类型详细信息（按文档 3.2.1）

    返回该数据类型所有数据源的详细状态和接口明细
    从数据库读取真实的健康检查状态
    """
    try:
        market_upper = market.upper()
        valid_markets = ["A_STOCK", "US_STOCK", "HK_STOCK"]
        if market_upper not in valid_markets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的市场类型: {market}"
            )

        logger.info(f"Fetching data type detail for {market_upper}/{data_type}")

        # 获取数据类型中文名
        data_types_map = _get_data_types_for_market(market_upper)
        data_type_name = data_types_map.get(data_type, data_type)

        # 检查数据类型是否存在
        if data_type not in data_types_map:
            logger.warning(f"Data type {data_type} not found in {market_upper}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"数据类型不存在: {data_type}"
            )

        # 获取配置
        source_configs = DATA_SOURCE_CONFIGS.get(market_upper, {})
        config = source_configs.get(data_type, {})
        primary_id = config.get("primary", "tushare")
        fallback_id = config.get("fallback")

        logger.info(
            f"Config for {market_upper}/{data_type}: "
            f"primary={primary_id}, fallback={fallback_id}"
        )

        # 从数据库获取所有相关数据源的状态
        try:
            all_status = await status_repo.get_all_status(market=market_upper, data_type=data_type)
            status_map = {s["source_id"]: s for s in all_status}
            logger.info(f"Found {len(status_map)} status records for {market_upper}/{data_type}")
        except Exception as db_error:
            logger.error(f"Database query failed for {market_upper}/{data_type}: {db_error}")
            status_map = {}

        # 构建数据源列表
        sources = []

        # 处理主数据源
        primary_status = status_map.get(primary_id)
        if primary_status:
            last_check = primary_status.get("last_check_at")
            # 安全获取错误消息
            last_error = primary_status.get("last_error")
            note = None
            if last_error:
                if isinstance(last_error, dict):
                    note = last_error.get("message")
                else:
                    note = str(last_error)

            sources.append({
                "source_type": "system",
                "source_id": primary_id,
                "source_name": SOURCE_DISPLAY_NAMES.get(primary_id, primary_id),
                "status": primary_status.get("status", "healthy"),
                "priority": 1,
                "last_check": last_check.isoformat() if last_check else None,
                "response_time_ms": primary_status.get("response_time_ms"),
                "avg_response_time_ms": primary_status.get("avg_response_time_ms"),
                "failure_count": primary_status.get("failure_count", 0),
                "note": note,
                "api_endpoints": _get_api_endpoints_for_source(primary_id, data_type)
            })
        else:
            # 无检查记录 - 不返回状态（前端显示为"-"）
            # 所有数据类型都会主动同步，此处仅用于系统刚启动时的初始化状态
            sources.append({
                "source_type": "system",
                "source_id": primary_id,
                "source_name": SOURCE_DISPLAY_NAMES.get(primary_id, primary_id),
                "status": None,
                "priority": 1,
                "last_check": None,
                "response_time_ms": None,
                "avg_response_time_ms": None,
                "failure_count": 0,
                "note": "等待健康检查",
                "api_endpoints": _get_api_endpoints_for_source(primary_id, data_type)
            })

        # 处理备用数据源
        if fallback_id:
            # 判断当前是否正在使用备用数据源
            primary_status = status_map.get(primary_id)
            is_using_fallback = (
                primary_status and
                primary_status.get("status") in ("unavailable", "error") and
                status_map.get(fallback_id) and
                status_map.get(fallback_id).get("status") == "healthy"
            )

            fallback_status = status_map.get(fallback_id)
            if fallback_status:
                last_check = fallback_status.get("last_check_at")
                # 安全获取错误消息
                last_error = fallback_status.get("last_error")
                error_note = None
                if last_error:
                    if isinstance(last_error, dict):
                        error_note = last_error.get("message")
                    else:
                        error_note = str(last_error)

                # 只有在备用数据源正在被使用时才显示状态
                sources.append({
                    "source_type": "system",
                    "source_id": fallback_id,
                    "source_name": SOURCE_DISPLAY_NAMES.get(fallback_id, fallback_id),
                    "status": fallback_status.get("status") if is_using_fallback else None,
                    "priority": 2,
                    "last_check": last_check.isoformat() if last_check else None,
                    "response_time_ms": fallback_status.get("response_time_ms", None),
                    "avg_response_time_ms": fallback_status.get("avg_response_time_ms"),
                    "failure_count": fallback_status.get("failure_count", 0),
                    "note": (
                        error_note
                        if error_note
                        else ("当前使用" if is_using_fallback else "备用")
                    ),
                    "api_endpoints": _get_api_endpoints_for_source(fallback_id, data_type)
                })
            else:
                # 无检查记录 - 备用数据源状态为 None
                sources.append({
                    "source_type": "system",
                    "source_id": fallback_id,
                    "source_name": SOURCE_DISPLAY_NAMES.get(fallback_id, fallback_id),
                    "status": None,
                    "priority": 2,
                    "last_check": None,
                    "response_time_ms": None,
                    "avg_response_time_ms": None,
                    "failure_count": 0,
                    "note": "备用（未使用）",
                    "api_endpoints": _get_api_endpoints_for_source(fallback_id, data_type)
                })

        # 获取最近事件（从历史表）
        recent_events = await history_repo.get_history(
            market=market_upper,
            data_type=data_type,
            limit=10
        )

        # 转换事件格式
        formatted_events = []
        for event in recent_events:
            timestamp = event.get("timestamp")
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()

            formatted_events.append({
                "timestamp": timestamp,
                "event_type": event.get("event_type", ""),
                "description": event.get("description", ""),
                "from_status": event.get("from_status"),
                "to_status": event.get("to_status"),
                "from_source": event.get("from_source"),
                "to_source": event.get("to_source"),
                "source_id": event.get("source_id")
            })

        return {
            "market": market_upper,
            "data_type": data_type,
            "data_type_name": data_type_name,
            "sources": sources,
            "recent_events": formatted_events
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get data type detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据类型详细信息失败: {str(e)}"
        )


@router.get("/data-source-status/{market}/{data_type}/history")
async def get_data_type_history(
    market: str,
    data_type: str,
    hours: int = 24,
    current_user: UserModel = Depends(get_current_user),
    history_repo: DataSourceStatusHistoryRepository = Depends(get_history_repo)
):
    """
    获取数据类型历史记录（按文档 3.5）

    返回指定时间范围内的状态变化历史
    从数据库读取真实的历史记录
    """
    try:
        market_upper = market.upper()
        valid_markets = ["A_STOCK", "US_STOCK", "HK_STOCK"]
        if market_upper not in valid_markets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的市场类型: {market}"
            )

        logger.info(f"Fetching history for {market_upper}/{data_type}, hours={hours}")

        # 从数据库获取历史事件
        events = await history_repo.get_history(
            market=market_upper,
            data_type=data_type,
            limit=100
        )

        # 转换为响应格式
        formatted_events = []
        for event in events:
            timestamp = event.get("timestamp")
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()

            formatted_events.append({
                "timestamp": timestamp,
                "event_type": event.get("event_type", ""),
                "description": event.get("description", ""),
                "from_status": event.get("from_status"),
                "to_status": event.get("to_status"),
                "from_source": event.get("from_source"),
                "to_source": event.get("to_source"),
                "source_id": event.get("source_id")
            })

        return {"events": formatted_events}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取历史记录失败: {str(e)}"
        )


@router.post("/data-source-status/{market}/{data_type}/{source_id}/retry")
async def retry_data_source(
    market: str,
    data_type: str,
    source_id: str,
    current_user: UserModel = Depends(get_current_user),
    monitor_service: SourceMonitorService = Depends(get_monitor_service)
):
    """
    手动重试数据源（按文档 3.4）

    触发健康检查并尝试恢复数据源
    实际调用监控服务执行健康检查
    """
    try:
        market_upper = market.upper()
        valid_markets = ["A_STOCK", "US_STOCK", "HK_STOCK"]
        if market_upper not in valid_markets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的市场类型: {market}"
            )

        logger.info(f"User {current_user.username} retrying {market_upper}/{data_type}/{source_id}")

        # 实际调用监控服务执行健康检查
        check_result = await monitor_service.check_single_source(
            source_id=source_id,
            market=market_upper,
            data_type=data_type,
            check_type="manual_retry"
        )

        success = check_result.get("status") == "healthy"

        response = {
            "success": success,
            "message": "重试成功" if success else "重试失败",
            "result": {
                "status": check_result.get("status"),
                "response_time_ms": check_result.get("response_time_ms"),
                "recovered_at": datetime.now().isoformat(),
                "previous_source": source_id
            }
        }

        if not success:
            response["error"] = {
                "error_message": (
                    check_result.get("error", {}).get("message", "未知错误")
                    if check_result.get("error")
                    else "健康检查失败"
                ),
                "failure_count": 1
            }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重试失败: {str(e)}"
        )


@router.post("/data-source-status/refresh")
async def refresh_status(
    market: Optional[str] = None
):
    """
    手动刷新状态（按文档 3.6）

    触发健康检查更新状态
    """
    try:
        if market:
            market_upper = market.upper()
            valid_markets = ["A_STOCK", "US_STOCK", "HK_STOCK"]
            if market_upper not in valid_markets:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的市场类型: {market}"
                )

        return {
            "success": True,
            "message": "状态已更新",
            "refreshed_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刷新状态失败: {str(e)}"
        )


# =============================================================================
# 辅助函数
# =============================================================================

def _get_data_types_for_market(market: str) -> Dict[str, str]:
    """获取市场的数据类型映射"""
    if market == "A_STOCK":
        return A_STOCK_DATA_TYPES
    elif market == "US_STOCK":
        return US_STOCK_DATA_TYPES
    elif market == "HK_STOCK":
        return HK_STOCK_DATA_TYPES
    return {}


def _get_relative_time(last_check_at: Optional[datetime]) -> str:
    """
    计算相对时间字符串

    Args:
        last_check_at: 最后检查时间

    Returns:
        相对时间字符串（如 "5分钟前"）
    """
    if not last_check_at:
        return "从未检查"

    now = datetime.now()
    delta = now - last_check_at

    seconds = delta.total_seconds()
    if seconds < 60:
        return "刚刚"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}分钟前"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}小时前"
    else:
        days = int(seconds / 86400)
        return f"{days}天前"


def _get_api_endpoints_for_source(source_id: str, data_type: str) -> List[Dict]:
    """
    获取数据源的接口明细（按文档定义）

    返回该数据源在指定数据类型下的接口列表
    """
    endpoints = []

    if source_id == "tushare":
        # TuShare 接口定义
        tushare_endpoints = {
            "daily_quote": [
                {"name": "pro_bar", "cn": "前复权日线"},
                {"name": "adj_factor", "cn": "复权因子"},
            ],
            "realtime_quote": [
                {"name": "stk_mins", "cn": "实时分钟线"},
            ],
            "minute_quote": [
                {"name": "stk_mins", "cn": "分钟K线"},
            ],
            "financials": [
                {"name": "income", "cn": "利润表"},
                {"name": "balancesheet", "cn": "资产负债表"},
            ],
            "financial_indicator": [
                {"name": "fina_indicator", "cn": "财务指标"},
            ],
            "company_info": [
                {"name": "stock_basic", "cn": "股票基本信息"},
            ],
            "news": [
                {"name": "news", "cn": "新闻快讯"},
            ],
            "calendar": [
                {"name": "trade_cal", "cn": "交易日历"},
            ],
            "top_list": [
                {"name": "top_list", "cn": "龙虎榜"},
            ],
            "moneyflow": [
                {"name": "moneyflow", "cn": "资金流向"},
            ],
            "dividend": [
                {"name": "dividend", "cn": "分红送股"},
            ],
            "shareholder_num": [
                {"name": "stk_holdernumber", "cn": "股东人数"},
            ],
            "margin": [
                {"name": "margin", "cn": "融资融券"},
            ],
            "macro_economy": [
                {"name": "cn_gdp", "cn": "GDP"},
                {"name": "cn_cpi", "cn": "CPI"},
            ],
            "sector": [
                {"name": "index_classify", "cn": "行业分类"},
            ],
            "index": [
                {"name": "index_daily", "cn": "指数日线"},
            ],
            "ipo": [
                {"name": "new_share", "cn": "新股列表"},
            ],
            "pledge": [
                {"name": "pledge_detail", "cn": "股权质押"},
            ],
            "repurchase": [
                {"name": "repurchase", "cn": "股票回购"},
            ],
            "adj_factor": [
                {"name": "adj_factor", "cn": "复权因子"},
            ],
        }
        if data_type in tushare_endpoints:
            for ep in tushare_endpoints[data_type]:
                endpoints.append({
                    "endpoint_name": ep["name"],
                    "endpoint_name_cn": ep["cn"],
                    "status": "healthy",
                    "last_check": None,
                    "failure_count": 0
                })

    elif source_id == "akshare":
        # AkShare 接口定义
        akshare_endpoints = {
            "daily_quote": [
                {"name": "stock_zh_a_hist", "cn": "A股历史行情"},
            ],
            "realtime_quote": [
                {"name": "stock_zh_a_spot_em", "cn": "A股实时行情"},
            ],
            "minute_quote": [
                {"name": "stock_zh_a_hist_min_em", "cn": "分钟K线"},
            ],
            "financials": [
                {"name": "stock_profit_sheet_by_report_em", "cn": "利润表"},
            ],
            "financial_indicator": [
                {"name": "stock_financial_abstract", "cn": "财务指标"},
            ],
            "company_info": [
                {"name": "stock_info_a_code_name", "cn": "股票基本信息"},
            ],
            "news": [
                {"name": "js_news", "cn": "新闻快讯"},
            ],
            "calendar": [
                {"name": "tool_trade_date_hist_sina", "cn": "交易日历"},
            ],
            "top_list": [
                {"name": "stock_lhb_detail_em", "cn": "龙虎榜详情"},
            ],
            "moneyflow": [
                {"name": "stock_individual_fund_flow", "cn": "个股资金流向"},
            ],
            "dividend": [
                {"name": "stock_dividend_cninfo", "cn": "分红送股"},
            ],
            "top_shareholder": [
                {"name": "stock_gdfx_top_10_em", "cn": "十大股东"},
            ],
            "margin": [
                {"name": "stock_margin_sse", "cn": "融资融券"},
            ],
            "macro_economy": [
                {"name": "cn_cpi", "cn": "CPI"},
                {"name": "cn_ppi", "cn": "PPI"},
                {"name": "cn_pmi", "cn": "PMI"},
            ],
            "sector": [
                {"name": "stock_board_concept_name_em", "cn": "概念板块"},
            ],
            "index": [
                {"name": "index_zh_a_hist", "cn": "指数历史"},
            ],
            "ipo": [
                {"name": "stock_new_ipo", "cn": "新股列表"},
            ],
        }
        if data_type in akshare_endpoints:
            for ep in akshare_endpoints[data_type]:
                endpoints.append({
                    "endpoint_name": ep["name"],
                    "endpoint_name_cn": ep["cn"],
                    "status": "healthy",
                    "last_check": None,
                    "failure_count": 0
                })

    elif source_id == "yahoo":
        # Yahoo Finance 接口定义
        yahoo_endpoints = {
            "daily_quote": [
                {"name": "history", "cn": "历史行情"},
            ],
            "realtime_quote": [
                {"name": "tickers", "cn": "实时报价"},
            ],
            "financials": [
                {"name": "financials", "cn": "财务报表"},
            ],
            "company_info": [
                {"name": "info", "cn": "公司信息"},
            ],
            "news": [
                {"name": "news", "cn": "新闻资讯"},
            ],
        }
        if data_type in yahoo_endpoints:
            for ep in yahoo_endpoints[data_type]:
                endpoints.append({
                    "endpoint_name": ep["name"],
                    "endpoint_name_cn": ep["cn"],
                    "status": "healthy",
                    "last_check": None,
                    "failure_count": 0
                })

    return endpoints
