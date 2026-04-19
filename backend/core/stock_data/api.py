"""
股票数据查询 API

两个路由器:
- stocks_router   → /api/stocks/{code}/quote|fundamentals|kline|news
- stock_data_router → /api/stock-data/basic-info|quotes|list|combined|search|markets|sync-status

全部委托 core.market_data 现有 repositories / services，不重复业务逻辑。
"""

import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from core.auth.dependencies import get_current_active_user
from core.auth.models import UserModel
from core.db.mongodb import mongodb

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 延迟获取 repositories / services（避免循环导入 + 启动时不需要全部就绪）
# ---------------------------------------------------------------------------

def _stock_info_repo():
    from core.market_data.repositories.stock_info import StockInfoRepository
    return StockInfoRepository()


def _stock_quote_repo():
    from core.market_data.repositories.stock_quotes import StockQuoteRepository
    return StockQuoteRepository()


def _stock_financial_repo():
    from core.market_data.repositories.stock_financial import StockFinancialRepository
    return StockFinancialRepository()


def _stock_financial_indicator_repo():
    from core.market_data.repositories.stock_financial import StockFinancialIndicatorRepository
    return StockFinancialIndicatorRepository()


def _market_news_repo():
    from core.market_data.repositories.market_news import MarketNewsRepository
    return MarketNewsRepository()


def _market_data_service():
    from core.market_data.services.market_data_service import MarketDataService
    return MarketDataService()


def _source_router():
    from core.market_data.managers.source_router import get_source_router
    return get_source_router()


def _infer_market(symbol: str) -> str:
    """从 symbol 推断市场类型字符串，供 source_router 使用"""
    if symbol.endswith((".SH", ".SZ", ".SSE", ".SZSE")):
        return "A_STOCK"
    if symbol.endswith(".HK"):
        return "HK_STOCK"
    if symbol.endswith(".US"):
        return "US_STOCK"
    return "A_STOCK"


def _serialize(doc: Optional[dict]) -> Optional[dict]:
    """MongoDB 文档序列化：移除 _id、转换 datetime"""
    if doc is None:
        return None
    doc.pop("_id", None)
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


def _serialize_list(docs: list[dict]) -> list[dict]:
    return [_serialize(d) for d in docs]


# ===================================================================
# Router 1: /api/stocks/*
# ===================================================================

stocks_router = APIRouter(prefix="/stocks", tags=["stocks"])


@stocks_router.get("/{code}/quote")
async def get_stock_quote(
    code: str,
    force_refresh: bool = Query(False, alias="force_refresh"),
    user: UserModel = Depends(get_current_active_user),
):
    """获取股票实时/最新行情"""
    from core.market_data.models import MarketType

    repo = _stock_quote_repo()
    market_str = _infer_market(code)
    market = MarketType(market_str)

    if force_refresh:
        # 尝试通过 source_router 实时获取
        try:
            router = _source_router()
            result = await router.route_to_best_source(
                market=market,
                method_name="get_daily_quotes",
                symbol=code,
            )
            if result:
                quotes = [q.model_dump() for q in result]
                if quotes:
                    latest = quotes[-1]
                    latest["code"] = code
                    latest["market"] = market_str
                    latest["updated_at"] = datetime.now().isoformat()
                    return {"success": True, "data": _serialize(latest)}
        except Exception as e:
            logger.warning(f"实时获取行情失败, 回退到数据库: {e}")

    # 从数据库取最新一条
    quote = await repo.get_latest_quote(code)
    if quote is None:
        return {"success": False, "data": None, "message": f"未找到 {code} 的行情数据"}

    quote["code"] = code
    return {"success": True, "data": _serialize(quote)}


@stocks_router.get("/{code}/fundamentals")
async def get_stock_fundamentals(
    code: str,
    source: Optional[str] = Query(None),
    force_refresh: bool = Query(False, alias="force_refresh"),
    user: UserModel = Depends(get_current_active_user),
):
    """获取基本面/财务数据"""
    fin_repo = _stock_financial_repo()
    ind_repo = _stock_financial_indicator_repo()
    info_repo = _stock_info_repo()

    # 获取股票基本信息（用于 name / industry）
    info = await info_repo.get_by_symbol(code)

    # 获取最新财务报表
    latest_fin = await fin_repo.get_latest_financial(code)

    # 获取最新财务指标
    latest_ind = await ind_repo.get_latest_indicator(code)

    result: dict[str, Any] = {
        "code": code,
        "name": info.get("name") if info else None,
        "industry": info.get("industry") if info else None,
        "market": info.get("market") if info else _infer_market(code),
        "sector": info.get("sector") if info else None,
    }

    # 合并指标数据
    if latest_ind:
        ind_data = _serialize(latest_ind)
        ind_data.pop("symbol", None)
        ind_data.pop("_id", None)
        for field in [
            "pe", "pb", "pe_ttm", "pb_mrq", "ps", "ps_ttm", "roe",
            "debt_ratio", "total_mv", "circ_mv", "turnover_rate", "volume_ratio",
        ]:
            if field in ind_data:
                result[field] = ind_data[field]

    if latest_fin:
        result["updated_at"] = latest_fin.get("updated_at")
        if isinstance(result["updated_at"], datetime):
            result["updated_at"] = result["updated_at"].isoformat()

    return {"success": True, "data": result}


@stocks_router.get("/{code}/kline")
async def get_stock_kline(
    code: str,
    period: str = Query("day"),
    limit: int = Query(120),
    adj: str = Query("none"),
    force_refresh: bool = Query(False, alias="force_refresh"),
    user: UserModel = Depends(get_current_active_user),
):
    """获取 K 线/蜡烛图数据"""
    from core.market_data.models import MarketType

    repo = _stock_quote_repo()

    # period 映射：前端 period → 后端处理逻辑
    # 目前只支持日线（数据库存的就是日线），分钟线需要走 minute_klines 集合
    if period in ("minute", "min", "1m", "5m", "15m", "30m", "60m"):
        # 分钟 K 线：查 stock_minute_klines 集合
        db = mongodb.database
        cursor = db["stock_minute_klines"].find(
            {"symbol": code}
        ).sort("trade_date", -1).limit(limit)
        raw_items = await cursor.to_list(length=limit)
        items = []
        for doc in raw_items:
            items.append({
                "time": doc.get("trade_date", ""),
                "open": doc.get("open"),
                "high": doc.get("high"),
                "low": doc.get("low"),
                "close": doc.get("close"),
                "volume": doc.get("volume"),
                "amount": doc.get("amount"),
            })
        return {
            "success": True,
            "data": {
                "code": code,
                "period": period,
                "limit": limit,
                "adj": adj,
                "items": items,
            },
        }

    # 日线 / 周线 / 月线
    if force_refresh:
        try:
            market = MarketType(_infer_market(code))
            router = _source_router()
            result = await router.route_to_best_source(
                market=market,
                method_name="get_daily_quotes",
                symbol=code,
            )
            if result:
                quotes = [q.model_dump() for q in result]
                quotes = quotes[-limit:]  # 只保留最近 limit 条
                items = []
                for q in quotes:
                    items.append({
                        "time": q.get("trade_date", ""),
                        "open": q.get("open"),
                        "high": q.get("high"),
                        "low": q.get("low"),
                        "close": q.get("close"),
                        "volume": q.get("volume"),
                        "amount": q.get("amount"),
                    })
                return {
                    "success": True,
                    "data": {
                        "code": code,
                        "period": period,
                        "limit": limit,
                        "adj": adj,
                        "source": "realtime",
                        "items": items,
                    },
                }
        except Exception as e:
            logger.warning(f"实时获取K线失败, 回退到数据库: {e}")

    # 从数据库查询
    quotes = await repo.get_quotes(symbol=code, limit=limit)
    items = []
    for q in reversed(quotes):  # get_quotes 默认降序，K线需要升序
        items.append({
            "time": q.get("trade_date", ""),
            "open": q.get("open"),
            "high": q.get("high"),
            "low": q.get("low"),
            "close": q.get("close"),
            "volume": q.get("volume"),
            "amount": q.get("amount"),
        })

    return {
        "success": True,
        "data": {
            "code": code,
            "period": period,
            "limit": limit,
            "adj": adj,
            "source": "database",
            "items": items,
        },
    }


@stocks_router.get("/{code}/news")
async def get_stock_news(
    code: str,
    days: int = Query(30),
    limit: int = Query(50),
    user: UserModel = Depends(get_current_active_user),
):
    """获取个股新闻"""
    repo = _market_news_repo()
    news_list = await repo.get_by_symbol(code, limit=limit)
    items = []
    for n in news_list:
        items.append({
            "title": n.title,
            "source": n.source,
            "time": n.datetime,
            "url": getattr(n, "url", None),
            "type": getattr(n, "news_type", None),
            "content": n.content,
            "summary": getattr(n, "summary", None),
        })
    return {
        "success": True,
        "data": {
            "code": code,
            "days": days,
            "limit": limit,
            "items": items,
        },
    }


# ===================================================================
# Router 2: /api/stock-data/*
# ===================================================================

stock_data_router = APIRouter(prefix="/stock-data", tags=["stock-data"])


@stock_data_router.get("/basic-info/{symbol}")
async def get_basic_info(
    symbol: str,
    user: UserModel = Depends(get_current_active_user),
):
    """根据 symbol 获取股票基础信息"""
    repo = _stock_info_repo()
    info = await repo.get_by_symbol(symbol)
    if info is None:
        return {"success": False, "data": None, "message": f"未找到 {symbol}"}
    return {"success": True, "data": _serialize(info)}


@stock_data_router.get("/quotes/{symbol}")
async def get_stock_data_quotes(
    symbol: str,
    user: UserModel = Depends(get_current_active_user),
):
    """获取最新行情（stock-data 版本）"""
    repo = _stock_quote_repo()
    quote = await repo.get_latest_quote(symbol)
    if quote is None:
        return {"success": False, "data": None, "message": f"未找到 {symbol} 的行情"}
    return {"success": True, "data": _serialize(quote)}


@stock_data_router.get("/list")
async def get_stock_list(
    market: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    user: UserModel = Depends(get_current_active_user),
):
    """分页获取股票列表"""
    repo = _stock_info_repo()

    filter_query: dict[str, Any] = {"status": "L"}
    if market:
        filter_query["market"] = market
    if industry:
        filter_query["industry"] = industry

    total = await repo.count_documents(filter_query)
    skip = (page - 1) * page_size

    stocks = await repo.find_many(
        filter_query,
        sort=[("symbol", 1)],
        limit=page_size,
        skip=skip,
    )

    # 尝试关联最新行情
    quote_repo = _stock_quote_repo()
    items = []
    for s in stocks:
        item = _serialize(s)
        # 精简字段以匹配前端 StockListItem
        latest = await quote_repo.get_latest_quote(s["symbol"])
        if latest:
            item["close"] = latest.get("close")
            item["pct_chg"] = latest.get("pct_chg")
        items.append(item)

    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@stock_data_router.get("/combined/{symbol}")
async def get_combined_stock_data(
    symbol: str,
    user: UserModel = Depends(get_current_active_user),
):
    """综合数据：基础信息 + 最新行情 + 财务指标"""
    info_repo = _stock_info_repo()
    quote_repo = _stock_quote_repo()
    ind_repo = _stock_financial_indicator_repo()

    info = await info_repo.get_by_symbol(symbol)
    quote = await quote_repo.get_latest_quote(symbol)

    return {
        "success": True,
        "data": {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "basic_info": _serialize(info),
            "quotes": _serialize(quote),
        },
    }


@stock_data_router.get("/search")
async def search_stocks(
    keyword: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    user: UserModel = Depends(get_current_active_user),
):
    """文本搜索股票（按 symbol / name 模糊匹配）"""
    import re

    repo = _stock_info_repo()

    # 构建正则搜索条件
    pattern = {"$regex": re.escape(keyword), "$options": "i"}
    filter_query = {
        "status": "L",
        "$or": [
            {"symbol": pattern},
            {"name": pattern},
            {"code": pattern},
        ],
    }

    results = await repo.find_many(filter_query, limit=limit)
    data = []
    for r in results:
        data.append({
            "symbol": r.get("symbol", ""),
            "name": r.get("name", ""),
            "market": r.get("market"),
            "industry": r.get("industry"),
        })

    return {
        "success": True,
        "data": {
            "data": data,
            "total": len(data),
            "keyword": keyword,
            "source": "database",
        },
    }


@stock_data_router.get("/markets")
async def get_market_summary(
    user: UserModel = Depends(get_current_active_user),
):
    """市场概览统计"""
    repo = _stock_info_repo()

    # 按市场分组统计
    pipeline = [
        {"$match": {"status": "L"}},
        {"$group": {"_id": "$market", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    breakdown = await repo.aggregate(pipeline)

    total = sum(b["count"] for b in breakdown)
    supported = [b["_id"] for b in breakdown if b["_id"]]

    return {
        "success": True,
        "data": {
            "total_stocks": total,
            "market_breakdown": breakdown,
            "supported_markets": supported,
            "last_updated": datetime.now().isoformat(),
        },
    }


@stock_data_router.get("/sync-status/quotes")
async def get_quotes_sync_status(
    user: UserModel = Depends(get_current_active_user),
):
    """获取各市场行情最近同步时间戳"""
    db = mongodb.database

    # 查 stock_quotes 按市场分组的最新 fetched_at
    pipeline = [
        {"$sort": {"fetched_at": -1}},
        {"$group": {
            "_id": "$market",
            "last_fetched": {"$first": "$fetched_at"},
            "data_source": {"$first": "$data_source"},
            "records_count": {"$sum": 1},
        }},
    ]
    cursor = db["stock_quotes"].aggregate(pipeline)
    results = await cursor.to_list(length=None)

    # 同时检查 data_sync_tasks 集合获取最近一次同步任务状态
    sync_task = await db["data_sync_tasks"].find_one(
        {"task_type": {"$regex": "quote"}},
        sort=[("created_at", -1)],
    )

    last_sync_time = None
    last_sync_time_iso = None
    data_source = None
    records_count = 0
    error_message = None
    success = True

    if results:
        # 取所有市场中最新的一次
        latest = max(results, key=lambda x: x.get("last_fetched") or datetime.min)
        last_fetched = latest.get("last_fetched")
        if isinstance(last_fetched, datetime):
            last_sync_time = last_fetched.strftime("%Y%m%d")
            last_sync_time_iso = last_fetched.isoformat()
        data_source = latest.get("data_source")
        records_count = sum(r.get("records_count", 0) for r in results)

    if sync_task:
        sync_status = sync_task.get("status", "")
        success = sync_status == "completed"
        if not success:
            error_message = sync_task.get("error_message")
        if not last_sync_time_iso and sync_task.get("completed_at"):
            ca = sync_task["completed_at"]
            if isinstance(ca, datetime):
                last_sync_time_iso = ca.isoformat()

    return {
        "success": True,
        "data": {
            "last_sync_time": last_sync_time,
            "last_sync_time_iso": last_sync_time_iso,
            "data_source": data_source,
            "success": success,
            "records_count": records_count,
            "error_message": error_message,
        },
    }
