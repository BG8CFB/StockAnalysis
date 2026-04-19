"""
用户自选股 API

提供 7 个 REST 端点，按 user_id 隔离数据。
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends

from core.auth.dependencies import get_current_active_user
from core.auth.models import UserModel
from core.favorites.models import AddFavoriteRequest, UpdateFavoriteRequest
from core.favorites.service import FavoriteRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/favorites", tags=["favorites"])

_fav_repo: Optional[FavoriteRepository] = None


def _get_repo() -> FavoriteRepository:
    """获取 FavoriteRepository 实例"""
    global _fav_repo
    if _fav_repo is None:
        _fav_repo = FavoriteRepository()
    return _fav_repo


@router.get("/")
async def list_favorites(
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取用户自选股列表"""
    repo = _get_repo()
    favorites = await repo.list_favorites(str(user.id))
    # 清理 _id 字段
    for fav in favorites:
        fav.pop("_id", None)
    return {"code": 0, "data": favorites, "message": "ok"}


@router.post("/")
async def add_favorite(
    req: AddFavoriteRequest,
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """添加自选股"""
    from datetime import datetime

    repo = _get_repo()
    data = {
        "user_id": str(user.id),
        "stock_code": req.stock_code,
        "stock_name": req.stock_name,
        "market": req.market,
        "tags": req.tags,
        "notes": req.notes,
        "alert_price_high": req.alert_price_high,
        "alert_price_low": req.alert_price_low,
        "current_price": None,
        "change_percent": None,
        "volume": None,
        "added_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    await repo.add_favorite(data)
    return {"code": 0, "data": {"stock_code": req.stock_code}, "message": "ok"}


@router.put("/{stock_code}")
async def update_favorite(
    stock_code: str,
    req: UpdateFavoriteRequest,
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """更新自选股（标签、备注、价格预警）"""
    repo = _get_repo()
    updates: Dict[str, Any] = {}
    if req.tags is not None:
        updates["tags"] = req.tags
    if req.notes is not None:
        updates["notes"] = req.notes
    if req.alert_price_high is not None:
        updates["alert_price_high"] = req.alert_price_high
    if req.alert_price_low is not None:
        updates["alert_price_low"] = req.alert_price_low

    if updates:
        await repo.update_favorite(str(user.id), stock_code, updates)

    return {"code": 0, "data": {"stock_code": stock_code}, "message": "ok"}


@router.delete("/{stock_code}")
async def remove_favorite(
    stock_code: str,
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """删除自选股"""
    repo = _get_repo()
    await repo.remove_favorite(str(user.id), stock_code)
    return {"code": 0, "data": {"stock_code": stock_code}, "message": "ok"}


@router.get("/check/{stock_code}")
async def check_favorite(
    stock_code: str,
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """检查股票是否在自选股中"""
    repo = _get_repo()
    is_fav = await repo.check_favorite(str(user.id), stock_code)
    return {
        "code": 0,
        "data": {"stock_code": stock_code, "is_favorite": is_fav},
        "message": "ok",
    }


@router.get("/tags")
async def get_favorite_tags(
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取用户所有标签"""
    repo = _get_repo()
    tags = await repo.get_all_tags(str(user.id))
    return {"code": 0, "data": tags, "message": "ok"}


@router.post("/sync-realtime")
async def sync_favorites_realtime(
    user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """同步自选股实时行情"""
    from datetime import datetime

    from core.market_data.services.data_sync_service import DataSyncService

    repo = _get_repo()
    stocks = await repo.get_all_stocks_for_sync(str(user.id))

    if not stocks:
        return {
            "code": 0,
            "data": {
                "total": 0,
                "success_count": 0,
                "failed_count": 0,
                "symbols": [],
                "data_source": "none",
                "message": "无自选股",
            },
            "message": "ok",
        }

    symbols = [s["stock_code"] for s in stocks]
    today = datetime.now().strftime("%Y%m%d")

    sync_service = DataSyncService()
    sync_result = await sync_service.sync_daily_quotes_with_fallback(
        symbols=symbols,
        start_date=today,
        end_date=today,
    )

    result_data = sync_result.get("result", {})
    success_count = result_data.get("successful", 0)
    failed_count = result_data.get("failed", 0)
    source = result_data.get("source", "unknown")

    return {
        "code": 0,
        "data": {
            "total": len(symbols),
            "success_count": success_count,
            "failed_count": failed_count,
            "symbols": symbols,
            "data_source": source,
            "message": f"同步完成: {success_count} 成功, {failed_count} 失败",
        },
        "message": "ok",
    }
