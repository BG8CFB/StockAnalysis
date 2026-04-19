"""
多市场查询 API 路由

5 个端点：
- GET /markets                                 支持的市场列表
- GET /markets/{market}/stocks/search          搜索股票
- GET /markets/{market}/stocks/{code}/info     股票详情
- GET /markets/{market}/stocks/{code}/quote    实时行情
- GET /markets/{market}/stocks/{code}/daily    日K线
"""

import logging
import re
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth.dependencies import get_current_active_user
from core.auth.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/markets", tags=["markets"])

# 支持的市场定义
MARKET_INFO: list[dict[str, Any]] = [
    {
        "code": "A_STOCK",
        "name": "A股",
        "name_en": "China A-Share",
        "currency": "CNY",
        "timezone": "Asia/Shanghai",
        "trading_hours": "09:30-11:30,13:00-15:00",
    },
    {
        "code": "US_STOCK",
        "name": "美股",
        "name_en": "US Stock",
        "currency": "USD",
        "timezone": "America/New_York",
        "trading_hours": "09:30-16:00 (ET)",
    },
    {
        "code": "HK_STOCK",
        "name": "港股",
        "name_en": "Hong Kong Stock",
        "currency": "HKD",
        "timezone": "Asia/Hong_Kong",
        "trading_hours": "09:30-12:00,13:00-16:00",
    },
]

MARKET_CODES = {m["code"] for m in MARKET_INFO}


def _serialize(doc: Optional[dict]) -> Optional[dict]:
    """序列化 MongoDB 文档"""
    if doc is None:
        return None
    doc.pop("_id", None)
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


def _stock_info_repo():
    from core.market_data.repositories.stock_info import StockInfoRepository
    return StockInfoRepository()


def _stock_quote_repo():
    from core.market_data.repositories.stock_quotes import StockQuoteRepository
    return StockQuoteRepository()


def _source_router():
    from core.market_data.managers.source_router import get_source_router
    return get_source_router()


def _infer_currency(market: str) -> str:
    for m in MARKET_INFO:
        if m["code"] == market:
            return m.get("currency", "")
    return ""


# ==================== 端点 ====================


@router.get("")
async def get_supported_markets(
    user: UserModel = Depends(get_current_active_user),
):
    """获取支持的市场列表"""
    return {"success": True, "data": {"markets": MARKET_INFO}}


@router.get("/{market}/stocks/search")
async def search_stocks(
    market: str,
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    user: UserModel = Depends(get_current_active_user),
):
    """搜索指定市场的股票"""
    market = market.upper()
    if market not in MARKET_CODES:
        raise HTTPException(status_code=400, detail=f"不支持的市场: {market}")

    repo = _stock_info_repo()

    pattern = {"$regex": re.escape(q), "$options": "i"}
    filter_query: dict[str, Any] = {
        "market": market,
        "status": "L",
        "$or": [
            {"symbol": pattern},
            {"name": pattern},
            {"code": pattern},
        ],
    }

    results = await repo.find_many(filter_query, limit=limit)

    stocks = []
    for r in results:
        stocks.append({
            "code": r.get("symbol", ""),
            "name": r.get("name", ""),
            "name_en": r.get("name_en"),
            "market": market,
            "source": "database",
        })

    return {"success": True, "data": {"stocks": stocks, "total": len(stocks)}}


@router.get("/{market}/stocks/{code}/info")
async def get_stock_info(
    market: str,
    code: str,
    user: UserModel = Depends(get_current_active_user),
):
    """获取指定市场的股票详情"""
    market = market.upper()
    if market not in MARKET_CODES:
        raise HTTPException(status_code=400, detail=f"不支持的市场: {market}")

    repo = _stock_info_repo()
    info = await repo.get_by_symbol(code)
    if info is None:
        # 尝试按 code + market 查询
        results = await repo.find_many(
            {"code": code, "market": market, "status": "L"}, limit=1
        )
        info = results[0] if results else None

    if info is None:
        raise HTTPException(status_code=404, detail=f"未找到股票: {code}")

    data = _serialize(info)
    data["currency"] = _infer_currency(market)

    return {
        "success": True,
        "data": {
            "code": data.get("symbol", code),
            "name": data.get("name", ""),
            "name_en": data.get("name_en"),
            "market": market,
            "source": "database",
            "total_mv": data.get("total_mv"),
            "pe": data.get("pe"),
            "pb": data.get("pb"),
            "currency": data.get("currency", ""),
        },
    }


@router.get("/{market}/stocks/{code}/quote")
async def get_stock_quote(
    market: str,
    code: str,
    user: UserModel = Depends(get_current_active_user),
):
    """获取指定市场的实时行情"""
    market = market.upper()
    if market not in MARKET_CODES:
        raise HTTPException(status_code=400, detail=f"不支持的市场: {market}")

    repo = _stock_quote_repo()
    quote = await repo.get_latest_quote(code)

    if quote is None:
        raise HTTPException(status_code=404, detail=f"未找到行情: {code}")

    data = _serialize(quote)
    return {
        "success": True,
        "data": {
            "code": code,
            "close": data.get("close"),
            "pct_chg": data.get("pct_chg"),
            "open": data.get("open"),
            "high": data.get("high"),
            "low": data.get("low"),
            "volume": data.get("volume"),
            "amount": data.get("amount"),
            "trade_date": data.get("trade_date"),
            "currency": _infer_currency(market),
        },
    }


@router.get("/{market}/stocks/{code}/daily")
async def get_daily_quotes(
    market: str,
    code: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(120, ge=1, le=1000),
    user: UserModel = Depends(get_current_active_user),
):
    """获取指定市场的日K线数据"""
    market = market.upper()
    if market not in MARKET_CODES:
        raise HTTPException(status_code=400, detail=f"不支持的市场: {market}")

    repo = _stock_quote_repo()
    quotes = await repo.get_quotes(
        symbol=code,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )

    items = []
    for q in reversed(quotes):
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
            "market": market,
            "quotes": items,
            "total": len(items),
        },
    }
