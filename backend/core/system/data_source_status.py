"""
数据状态监控 API
提供前端仪表板使用的统一接口
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from core.auth.dependencies import get_current_user
from core.market_data.services.source_monitor_service import SourceMonitorService
from core.market_data.managers.source_router import DataSourceRouter
from core.market_data.config.schemas import DashboardOverviewResponse, MarketDetailResponse, DataTypeDetailResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/core/system", tags=["系统管理_数据源监控"])


def get_monitor_service() -> SourceMonitorService:
    """获取监控服务实例"""
    return SourceMonitorService()


def get_source_router() -> DataSourceRouter:
    """获取数据源路由器实例"""
    from core.market_data.config import get_config
    config = get_config()
    return DataSourceRouter.create_default_router(tushare_token=config.tushare_token)


# ==================== 仪表板概览 ====================

@router.get("/data-source-status/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    monitor_service: SourceMonitorService = Depends(get_monitor_service)
):
    """
    获取数据状态监控仪表板概览

    返回各市场的数据源状态汇总信息
    """
    try:
        logger.info("Fetching dashboard overview for data source status")
        
        # 获取所有市场的状态汇总
        summary = await monitor_service.get_status_summary()
        
        # 获取当前时间
        from datetime import datetime
        current_time = datetime.now()
        
        overview = {}
        
        # 处理A股数据
        if "A_STOCK" in summary.get("markets", {}):
            a_stock_data = summary["markets"]["A_STOCK"]
            overview["a_stock"] = {
                "status": a_stock_data.get("overall_status", "unavailable"),
                "last_update": current_time.isoformat(),
                "last_update_relative": "刚刚"
            }
        
        # 处理美股数据
        if "US_STOCK" in summary.get("markets", {}):
            us_stock_data = summary["markets"]["US_STOCK"]
            overview["us_stock"] = {
                "status": us_stock_data.get("overall_status", "unavailable"),
                "last_update": current_time.isoformat(),
                "last_update_relative": "刚刚"
            }
        
        # 处理港股数据
        if "HK_STOCK" in summary.get("markets", {}):
            hk_stock_data = summary["markets"]["HK_STOCK"]
            overview["hk_stock"] = {
                "status": hk_stock_data.get("overall_status", "unavailable"),
                "last_update": current_time.isoformat(),
                "last_update_relative": "刚刚",
                "reason": "Not implemented yet"
            }
        
        return DashboardOverviewResponse(**overview)
        
    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取仪表板概览失败: {str(e)}"
        )


# ==================== 市场详细状态 ====================

@router.get("/data-source-status/{market_type}")
async def get_market_detail(
    market_type: str,
    monitor_service: SourceMonitorService = Depends(get_monitor_service)
):
    """
    获取指定市场的数据源详细状态

    返回该市场各数据类型的数据源状态
    """
    try:
        logger.info(f"Fetching market detail for {market_type}")
        
        # 验证市场类型
        valid_markets = ["A_STOCK", "US_STOCK", "HK_STOCK"]
        if market_type.upper() not in valid_markets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的市场类型: {market_type}。有效值: {', '.join(valid_markets)}"
            )
        
        # 获取该市场的数据类型列表
        data_types = []
        
        if market_type.upper() == "A_STOCK":
            data_types = [
                {"name": "stock_list", "display_name": "股票列表"},
                {"name": "daily_quotes", "display_name": "日线行情"},
                {"name": "minute_quotes", "display_name": "分钟K线"},
                {"name": "financials", "display_name": "财务数据"},
                {"name": "company_info", "display_name": "公司信息"},
            ]
        elif market_type.upper() == "US_STOCK":
            data_types = [
                {"name": "stock_list", "display_name": "股票列表"},
                {"name": "daily_quotes", "display_name": "日线行情"},
                {"name": "financials", "display_name": "财务数据"},
                {"name": "company_info", "display_name": "公司信息"},
                {"name": "macro_economic", "display_name": "宏观经济"},
            ]
        elif market_type.upper() == "HK_STOCK":
            data_types = [
                {"name": "stock_list", "display_name": "股票列表"},
                {"name": "daily_quotes", "display_name": "日线行情"},
            ]
        
        market_data = []
        
        for data_type in data_types:
            try:
                # 获取该数据类型的状态
                status_list = await monitor_service.get_source_status(
                    source_id="all",  # 获取所有数据源
                    market=market_type.upper()
                )
                
                # 过滤出当前数据类型的状态
                relevant_status = [s for s in status_list if s.get("data_type") == data_type["name"]]
                
                # 找到当前活动的数据源
                current_source = None
                fallback_used = False
                retry_possible = False
                primary_source = None
                fallback_reason = None
                
                for status in relevant_status:
                    if status.get("status") in ["healthy", "degraded"]:
                        current_source = status
                        fallback_used = status.get("is_fallback", False)
                        if fallback_used:
                            fallback_reason = status.get("fallback_reason")
                        break
                
                # 如果没有找到健康的源，查看降级源
                if not current_source:
                    for status in relevant_status:
                        if status.get("status") == "degraded":
                            current_source = status
                            break
                
                # 如果没有找到任何源，使用第一个源
                if not current_source and relevant_status:
                    current_source = relevant_status[0]
                
                if current_source:
                    data_type_info = {
                        "data_type": data_type["name"],
                        "data_type_name": data_type["display_name"],
                        "current_source": {
                            "source_type": current_source.get("source_type", "system"),
                            "source_id": current_source.get("source_id", "unknown"),
                            "source_name": current_source.get("source_name", "未知数据源"),
                            "status": current_source.get("status", "unavailable"),
                            "last_check": current_source.get("last_check", ""),
                            "last_check_relative": "刚刚"
                        },
                        "is_fallback": fallback_used,
                        "can_retry": retry_possible
                    }
                    
                    if fallback_used and fallback_reason:
                        data_type_info["fallback_reason"] = fallback_reason
                    
                    market_data.append(data_type_info)
                
            except Exception as e:
                logger.error(f"Error processing {data_type['name']}: {e}")
        
        # 构建市场详细信息
        market_name_map = {
            "A_STOCK": "A股",
            "US_STOCK": "美股",
            "HK_STOCK": "港股"
        }
        
        market_detail = {
            "market": market_type.upper(),
            "market_name": market_name_map.get(market_type.upper(), market_type.upper()),
            "data_types": market_data
        }
        
        return JSONResponse(content=market_detail)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get market detail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取市场详细状态失败: {str(e)}"
        )


# ==================== 数据类型详细信息 ====================

@router.get("/data-source-status/{market_type}/{data_type}")
async def get_data_type_detail(
    market_type: str,
    data_type: str,
    monitor_service: SourceMonitorService = Depends(get_monitor_service)
):
    """
    获取指定数据类型的详细信息

    返回该数据类型所有数据源的状态信息
    """
    try:
        logger.info(f"Fetching data type detail for {market_type}/{data_type}")
        
        # 验证市场类型
        valid_markets = ["A_STOCK", "US_STOCK", "HK_STOCK"]
        if market_type.upper() not in valid_markets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的市场类型: {market_type}"
            )
        
        # 获取所有数据源的状态
        status_list = await monitor_service.get_source_status(
            source_id="all",
            market=market_type.upper()
        )
        
        # 过滤出指定数据类型的状态
        relevant_status = [
            s for s in status_list 
            if s.get("data_type") == data_type
        ]
        
        sources = []
        recent_events = []
        
        for status in relevant_status:
            source_detail = {
                "source_type": status.get("source_type", "system"),
                "source_id": status.get("source_id", "unknown"),
                "source_name": status.get("source_name", "未知数据源"),
                "status": status.get("status", "unavailable"),
                "priority": status.get("priority", 1),
                "last_check": status.get("last_check", ""),
                "response_time_ms": status.get("response_time_ms"),
                "avg_response_time_ms": status.get("avg_response_time_ms"),
                "failure_count": status.get("failure_count", 0)
            }
            sources.append(source_detail)
        
        # 获取最近的事件
        events = await monitor_service.get_recent_events(hours=24)
        market_events = [
            e for e in events
            if e.get("market") == market_type.upper() and e.get("data_type") == data_type
        ]
        
        for event in market_events[:10]:  # 最多返回10个事件
            recent_events.append({
                "timestamp": event.get("timestamp", ""),
                "event_type": event.get("event_type", ""),
                "description": event.get("description", ""),
                "from_status": event.get("from_status"),
                "to_status": event.get("to_status"),
                "from_source": event.get("from_source"),
                "to_source": event.get("to_source"),
                "source_id": event.get("source_id")
            })
        
        # 构建数据类型详细信息
        data_type_name_map = {
            "stock_list": "股票列表",
            "daily_quotes": "日线行情",
            "minute_quotes": "分钟K线",
            "financials": "财务数据",
            "company_info": "公司信息",
            "macro_economic": "宏观经济",
            "technical_indicators": "技术指标"
        }
        
        detail_response = {
            "market": market_type.upper(),
            "data_type": data_type,
            "data_type_name": data_type_name_map.get(data_type, data_type),
            "sources": sources,
            "recent_events": recent_events
        }
        
        return JSONResponse(content=detail_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get data type detail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据类型详细信息失败: {str(e)}"
        )


# ==================== 错误详情 ====================

@router.get("/data-source-status/{market_type}/{data_type}/{source_id}/error")
async def get_error_detail(
    market_type: str,
    data_type: str,
    source_id: str,
    current_user: dict = Depends(get_current_user),
    monitor_service: SourceMonitorService = Depends(get_monitor_service)
):
    """
    获取错误详情

    返回指定数据源的错误信息
    """
    try:
        logger.info(f"Fetching error detail for {market_type}/{data_type}/{source_id}")
        
        # 验证市场类型
        valid_markets = ["A_STOCK", "US_STOCK", "HK_STOCK"]
        if market_type.upper() not in valid_markets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的市场类型: {market_type}"
            )
        
        # 获取错误详情（便于化实现）
        error_detail = {
            "market": market_type.upper(),
            "data_type": data_type,
            "source_id": source_id,
            "source_name": f"{source_id} (测试)",
            "error": {
                "error_code": "TEST_404",
                "error_message": "测试错误详情接口",
                "failure_count": 0
            }
        }
        
        # 如果是管理员，添加调试信息
        from core.auth.rbac import Role
        if current_user.get("role") in [Role.ADMIN, Role.SUPER_ADMIN]:
            error_detail["admin_debug_info"] = {
                "note": "管理员调试信息需连接真实监控服务",
                "traceback": "Not implemented yet"
            }
        
        return JSONResponse(content=error_detail)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get error detail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取错误详情失败: {str(e)}"
        )


# ==================== 重试数据源 ====================

@router.post("/data-source-status/{market_type}/{data_type}/{source_id}/retry")
async def retry_data_source(
    market_type: str,
    data_type: str,
    source_id: str,
    current_user: dict = Depends(get_current_user),
    monitor_service: SourceMonitorService = Depends(get_monitor_service),
    source_router: DataSourceRouter = Depends(get_source_router)
):
    """
    重试数据源

    手动重试指定的数据源
    """
    try:
        logger.info(f"Retrying data source: {market_type}/{data_type}/{source_id}")
        
        # 验证市场类型
        valid_markets = ["A_STOCK", "US_STOCK", "HK_STOCK"]
        if market_type.upper() not in valid_markets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的市场类型: {market_type}"
            )
        
        # 执行健康检查
        result = await monitor_service.check_single_source(
            source_id=source_id,
            market=market_type.upper(),
            data_type=data_type,
            check_type="manual_retry"
        )
        
        retry_response = {
            "success": result.get("status") in ["healthy", "degraded"],
            "message": result.get("message", "重试完成"),
            "result": {
                "status": result.get("status", "unknown"),
                "response_time_ms": result.get("response_time_ms", 0),
                "recovered_at": result.get("check_time", ""),
                "was_fallback": result.get("is_fallback", False),
                "previous_source": result.get("previous_source", source_id)
            }
        }
        
        if result.get("status") in ["unavailable", "failed"]:
            retry_response["error"] = {
                "error_message": result.get("error", "重试失败"),
                "failure_count": result.get("failure_count", 1)
            }
        
        return JSONResponse(content=retry_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry data source: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重试数据源失败: {str(e)}"
        )


# ==================== 刷新状态 ====================

@router.post("/data-source-status/refresh")
async def refresh_status(
    market: Optional[str] = None,
    monitor_service: SourceMonitorService = Depends(get_monitor_service)
):
    """
    手动刷新数据源状态

    触发一次完整的数据源健康检查
    """
    try:
        logger.info(f"Refreshing data source status for market: {market}")
        
        if market:
            valid_markets = ["A_STOCK", "US_STOCK", "HK_STOCK"]
            if market.upper() not in valid_markets:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的市场类型: {market}"
                )
            
            result = await monitor_service.check_all_sources(
                market=market.upper(),
                check_type="manual_refresh"
            )
        else:
            result = await monitor_service.check_all_sources(
                check_type="manual_refresh"
            )
        
        refresh_response = {
            "success": True,
            "message": "状态刷新完成",
            "refreshed_at": datetime.now().isoformat()
        }
        
        return JSONResponse(content=refresh_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刷新状态失败: {str(e)}"
        )
