"""
市场数据模块API路由

提供数据查询和同步的HTTP接口
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from modules.market_data.schemas import (
    StockListRequest,
    QuoteQueryRequest,
    FinancialQueryRequest,
    DataSyncRequest,
    StockInfoResponse,
    QuoteResponse,
    FinancialResponse,
    IndicatorResponse,
    DataSourceHealthResponse,
    DataSyncResponse,
)
from modules.market_data.models import MarketType
from modules.market_data.repositories.stock_info import StockInfoRepository
from modules.market_data.repositories.stock_quotes import StockQuoteRepository
from modules.market_data.repositories.stock_financial import (
    StockFinancialRepository,
    StockFinancialIndicatorRepository,
)
from modules.market_data.repositories.datasource import (
    SystemDataSourceRepository,
    DataSourceStatusRepository,
    DataSourceStatusHistoryRepository,
)
from modules.market_data.managers.source_router import DataSourceRouter
from modules.market_data.services.data_sync_service import DataSyncService
from modules.market_data.services.source_monitor_service import SourceMonitorService
from modules.market_data.config import get_config

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/market-data", tags=["市场数据"])

# 全局数据源路由器实例（在启动时初始化）
_source_router: DataSourceRouter = None
_data_sync_service: DataSyncService = None
_source_monitor_service: SourceMonitorService = None

def get_source_router() -> DataSourceRouter:
    """获取数据源路由器实例"""
    global _source_router
    if _source_router is None:
        config = get_config()
        _source_router = DataSourceRouter.create_default_router(
            tushare_token=config.tushare_token
        )
    return _source_router

def get_data_sync_service() -> DataSyncService:
    """获取数据同步服务实例"""
    global _data_sync_service
    if _data_sync_service is None:
        _data_sync_service = DataSyncService()
    return _data_sync_service

def get_source_monitor_service() -> SourceMonitorService:
    """获取数据源监控服务实例"""
    global _source_monitor_service
    if _source_monitor_service is None:
        _source_monitor_service = SourceMonitorService()
    return _source_monitor_service


# ==================== 股票信息接口 ====================

@router.post("/stocks/list", response_model=List[StockInfoResponse])
async def get_stock_list(
    request: StockListRequest,
    source_router: DataSourceRouter = Depends(get_source_router)
):
    """
    获取股票列表

    从数据源获取股票列表，支持按市场类型筛选
    """
    try:
        logger.info(f"Fetching stock list for market {request.market.value}")

        # 通过路由器获取数据（自动降级）
        stocks = await source_router.route_to_best_source(
            market=request.market,
            method_name="get_stock_list",
            status=request.status
        )

        return [
            StockInfoResponse(
                symbol=stock.symbol,
                market=stock.market,
                name=stock.name,
                industry=stock.industry,
                sector=stock.sector,
                listing_date=stock.listing_date,
                exchange=stock.exchange.value,
                status=stock.status,
                data_source=stock.data_source
            )
            for stock in stocks
        ]

    except Exception as e:
        logger.error(f"Failed to get stock list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取股票列表失败: {str(e)}"
        )


@router.get("/stocks/{symbol}/info", response_model=StockInfoResponse)
async def get_stock_info(symbol: str):
    """
    获取股票详细信息

    从数据库查询股票信息
    """
    try:
        repo = StockInfoRepository()
        stock_data = await repo.get_by_symbol(symbol)

        if not stock_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"股票信息不存在: {symbol}"
            )

        return StockInfoResponse(**stock_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stock info for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取股票信息失败: {str(e)}"
        )


# ==================== 行情数据接口 ====================

@router.post("/quotes/query", response_model=List[QuoteResponse])
async def query_quotes(request: QuoteQueryRequest):
    """
    查询历史行情

    从数据库查询股票的历史行情数据
    """
    try:
        repo = StockQuoteRepository()
        quotes_data = await repo.get_quotes(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=request.limit
        )

        return [
            QuoteResponse(
                symbol=q['symbol'],
                trade_date=q['trade_date'],
                open=q['open'],
                high=q['high'],
                low=q['low'],
                close=q['close'],
                volume=q['volume'],
                amount=q.get('amount'),
                change=q.get('change'),
                change_pct=q.get('change_pct'),
                data_source=q['data_source']
            )
            for q in quotes_data
        ]

    except Exception as e:
        logger.error(f"Failed to query quotes for {request.symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询行情数据失败: {str(e)}"
        )


@router.get("/quotes/{symbol}/latest", response_model=QuoteResponse)
async def get_latest_quote(symbol: str):
    """
    获取最新行情

    查询指定股票的最新行情数据
    """
    try:
        repo = StockQuoteRepository()
        quote_data = await repo.get_latest_quote(symbol)

        if not quote_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"行情数据不存在: {symbol}"
            )

        return QuoteResponse(
            symbol=quote_data['symbol'],
            trade_date=quote_data['trade_date'],
            open=quote_data['open'],
            high=quote_data['high'],
            low=quote_data['low'],
            close=quote_data['close'],
            volume=quote_data['volume'],
            amount=quote_data.get('amount'),
            change=quote_data.get('change'),
            change_pct=quote_data.get('change_pct'),
            data_source=quote_data['data_source']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest quote for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取最新行情失败: {str(e)}"
        )


# ==================== 财务数据接口 ====================

@router.post("/financials/query", response_model=List[FinancialResponse])
async def query_financials(request: FinancialQueryRequest):
    """
    查询财务数据

    从数据库查询股票的财务报表数据
    """
    try:
        repo = StockFinancialRepository()
        financials_data = await repo.get_financials(
            symbol=request.symbol,
            report_type=request.report_type,
            limit=request.limit
        )

        return [
            FinancialResponse(
                symbol=f['symbol'],
                report_date=f['report_date'],
                report_type=f['report_type'],
                publish_date=f.get('publish_date'),
                income_statement=f.get('income_statement'),
                balance_sheet=f.get('balance_sheet'),
                cash_flow=f.get('cash_flow'),
                data_source=f['data_source']
            )
            for f in financials_data
        ]

    except Exception as e:
        logger.error(f"Failed to query financials for {request.symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询财务数据失败: {str(e)}"
        )


@router.get("/indicators/{symbol}/latest")
async def get_latest_indicators(symbol: str):
    """
    获取最新财务指标

    查询指定股票的最新财务指标
    """
    try:
        repo = StockFinancialIndicatorRepository()
        indicator_data = await repo.get_latest_indicator(symbol)

        if not indicator_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"财务指标不存在: {symbol}"
            )

        return indicator_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest indicators for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取财务指标失败: {str(e)}"
        )


# ==================== 数据同步接口 ====================

@router.post("/sync/stock-list")
async def sync_stock_list(
    market: str = "A_STOCK",
    source_id: str = "tushare",
    status: str = "L",
    sync_service: DataSyncService = Depends(get_data_sync_service)
):
    """
    同步股票列表

    从数据源同步股票列表到数据库
    """
    try:
        from modules.market_data.models import MarketType

        market_type = MarketType(market)
        result = await sync_service.sync_stock_list(
            market=market_type,
            source_id=source_id,
            status=status
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Failed to sync stock list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步股票列表失败: {str(e)}"
        )


@router.post("/sync/daily-quotes")
async def sync_daily_quotes(
    symbols: List[str],
    start_date: str,
    end_date: str,
    source_id: str = "tushare",
    adjust_type: Optional[str] = None,
    sync_service: DataSyncService = Depends(get_data_sync_service)
):
    """
    同步日线行情

    从数据源同步指定股票的日线行情到数据库
    """
    try:
        result = await sync_service.sync_daily_quotes(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            source_id=source_id,
            adjust_type=adjust_type
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Failed to sync daily quotes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步日线行情失败: {str(e)}"
        )


@router.post("/sync/minute-quotes")
async def sync_minute_quotes(
    symbols: List[str],
    trade_date: str,
    source_id: str = "akshare",
    freq: str = "1min",
    sync_service: DataSyncService = Depends(get_data_sync_service)
):
    """
    同步分钟K线数据

    从数据源同步指定股票的分钟K线到数据库
    """
    try:
        result = await sync_service.sync_minute_quotes(
            symbols=symbols,
            trade_date=trade_date,
            source_id=source_id,
            freq=freq
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Failed to sync minute quotes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步分钟K线失败: {str(e)}"
        )


@router.post("/sync/financials")
async def sync_financials(
    symbols: List[str],
    report_date: Optional[str] = None,
    source_id: str = "tushare",
    sync_service: DataSyncService = Depends(get_data_sync_service)
):
    """
    同步财务数据

    从数据源同步指定股票的财务数据到数据库
    """
    try:
        result = await sync_service.sync_financials(
            symbols=symbols,
            report_date=report_date,
            source_id=source_id
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Failed to sync financials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步财务数据失败: {str(e)}"
        )


@router.post("/sync/company-info")
async def sync_company_info(
    symbols: List[str],
    source_id: str = "tushare",
    sync_service: DataSyncService = Depends(get_data_sync_service)
):
    """
    同步公司信息

    从数据源同步指定股票的公司信息到数据库
    """
    try:
        result = await sync_service.sync_company_info(
            symbols=symbols,
            source_id=source_id
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Failed to sync company info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步公司信息失败: {str(e)}"
        )


@router.post("/sync/macro-economic")
async def sync_macro_economic(
    indicators: List[str],
    source_id: str = "tushare",
    sync_service: DataSyncService = Depends(get_data_sync_service)
):
    """
    同步宏观经济数据

    从数据源同步宏观经济数据到数据库
    """
    try:
        result = await sync_service.sync_macro_economic(
            indicators=indicators,
            source_id=source_id
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Failed to sync macro economic: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步宏观经济数据失败: {str(e)}"
        )


# ==================== 数据源健康检查接口 ====================

@router.get("/health", response_model=List[DataSourceHealthResponse])
async def check_data_sources_health(
    source_router: DataSourceRouter = Depends(get_source_router)
):
    """
    检查所有数据源的健康状态

    返回各数据源的可用性、响应时间等信息
    """
    try:
        health_report = await source_router.check_all_sources_health()

        return [
            DataSourceHealthResponse(
                source_name=source_name,
                is_available=health['is_available'],
                response_time_ms=health.get('response_time_ms'),
                last_check_time=health.get('last_check_time'),
                failure_count=health.get('failure_count', 0),
                error=health.get('error')
            )
            for source_name, health in health_report.items()
        ]

    except Exception as e:
        logger.error(f"Failed to check data sources health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"健康检查失败: {str(e)}"
        )


@router.post("/health/check")
async def check_single_source_health(
    source_id: str,
    market: str = "A_STOCK",
    data_type: str = "stock_list",
    monitor_service: SourceMonitorService = Depends(get_source_monitor_service)
):
    """
    检查单个数据源的健康状态

    对指定数据源的指定数据类型执行健康检查
    """
    try:
        result = await monitor_service.check_single_source(
            source_id=source_id,
            market=market,
            data_type=data_type,
            check_type="manual_check"
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Failed to check source health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查数据源健康状态失败: {str(e)}"
        )


@router.post("/health/check-all")
async def check_all_sources_health(
    market: Optional[str] = None,
    check_type: str = "manual_check",
    monitor_service: SourceMonitorService = Depends(get_source_monitor_service)
):
    """
    检查所有数据源的健康状态

    对所有数据源执行健康检查
    """
    try:
        result = await monitor_service.check_all_sources(
            market=market,
            check_type=check_type
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Failed to check all sources health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查所有数据源健康状态失败: {str(e)}"
        )


# ==================== 数据源状态监控接口 ====================

@router.get("/monitor/status-summary")
async def get_status_summary(
    market: Optional[str] = None,
    monitor_service: SourceMonitorService = Depends(get_source_monitor_service)
):
    """
    获取数据源状态汇总

    返回各数据源的健康状态统计
    """
    try:
        summary = await monitor_service.get_status_summary(market=market)
        return JSONResponse(content=summary)

    except Exception as e:
        logger.error(f"Failed to get status summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取状态汇总失败: {str(e)}"
        )


@router.get("/monitor/source-status/{source_id}")
async def get_source_status(
    source_id: str,
    market: str = "A_STOCK",
    monitor_service: SourceMonitorService = Depends(get_source_monitor_service)
):
    """
    获取指定数据源的所有状态

    返回该数据源各数据类型的健康状态
    """
    try:
        status_list = await monitor_service.get_source_status(
            source_id=source_id,
            market=market
        )
        return JSONResponse(content=status_list)

    except Exception as e:
        logger.error(f"Failed to get source status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据源状态失败: {str(e)}"
        )


# ==================== 错误查询接口 ====================

@router.get("/monitor/recent-events")
async def get_recent_events(
    hours: int = 24,
    limit: int = 100,
    monitor_service: SourceMonitorService = Depends(get_source_monitor_service)
):
    """
    获取最近的失败/错误事件

    返回指定时间范围内的错误事件记录
    """
    try:
        events = await monitor_service.get_recent_events(
            hours=hours,
            limit=limit
        )
        return JSONResponse(content=events)

    except Exception as e:
        logger.error(f"Failed to get recent events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取最近事件失败: {str(e)}"
        )


@router.get("/monitor/source-history/{source_id}")
async def get_source_history(
    source_id: str,
    event_type: Optional[str] = None,
    limit: int = 50,
    monitor_service: SourceMonitorService = Depends(get_source_monitor_service)
):
    """
    获取指定数据源的历史记录

    返回该数据源的状态变更历史
    """
    try:
        history = await monitor_service.get_source_history(
            source_id=source_id,
            event_type=event_type,
            limit=limit
        )
        return JSONResponse(content=history)

    except Exception as e:
        logger.error(f"Failed to get source history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据源历史记录失败: {str(e)}"
        )


@router.get("/monitor/error-statistics")
async def get_error_statistics(
    hours: int = 24,
    monitor_service: SourceMonitorService = Depends(get_source_monitor_service)
):
    """
    获取错误统计信息

    返回指定时间范围内的错误统计数据
    """
    try:
        statistics = await monitor_service.get_error_statistics(hours=hours)
        return JSONResponse(content=statistics)

    except Exception as e:
        logger.error(f"Failed to get error statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取错误统计失败: {str(e)}"
        )


# ==================== 数据源配置接口 ====================

@router.get("/sources/configs")
async def get_source_configs(
    market: Optional[str] = None,
    enabled_only: bool = True,
    system_source_repo: SystemDataSourceRepository = Depends(lambda: SystemDataSourceRepository())
):
    """
    获取数据源配置列表

    返回系统数据源的配置信息
    """
    try:
        if market:
            configs = await system_source_repo.get_enabled_configs(
                market=market,
                enabled=enabled_only
            )
        else:
            all_configs = []
            for m in ["A_STOCK", "US_STOCK", "HK_STOCK"]:
                all_configs.extend(await system_source_repo.get_enabled_configs(market=m, enabled=enabled_only))
            configs = all_configs

        return JSONResponse(content=configs)

    except Exception as e:
        logger.error(f"Failed to get source configs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据源配置失败: {str(e)}"
        )


@router.get("/sources/config/{source_id}")
async def get_source_config(
    source_id: str,
    market: str = "A_STOCK",
    system_source_repo: SystemDataSourceRepository = Depends(lambda: SystemDataSourceRepository())
):
    """
    获取单个数据源配置

    返回指定数据源的配置信息
    """
    try:
        config = await system_source_repo.get_config(
            source_id=source_id,
            market=market
        )

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"数据源配置不存在: {source_id}"
            )

        return JSONResponse(content=config)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据源配置失败: {str(e)}"
        )
