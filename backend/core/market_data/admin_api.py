"""
市场数据模块API路由

提供用户数据源配置接口

注意：数据查询和同步接口已删除，仅保留用户数据源配置功能。
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.market_data.repositories.datasource import (
    SystemDataSourceRepository,
    UserDataSourceRepository,
)
from core.auth.dependencies import get_current_active_user
from core.user.models import UserModel
from core.config import SUPPORTED_MARKETS

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/market-data", tags=["市场数据"])


# =============================================================================
# 请求/响应模型
# =============================================================================

class UserSourceConfigCreate(BaseModel):
    """创建用户数据源配置请求"""
    source_id: str = Field(..., description="数据源 ID")
    market: str = Field(..., description="市场类型: A_STOCK, US_STOCK, HK_STOCK")
    api_key: str = Field(..., description="API 密钥")
    enabled: bool = Field(default=True, description="是否启用")
    priority: int = Field(default=1, description="优先级")


class UserSourceConfigUpdate(BaseModel):
    """更新用户数据源配置请求"""
    api_key: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None


# =============================================================================
# 系统数据源配置查询接口（只读）
# =============================================================================

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
                enabled_only=enabled_only
            )
        else:
            all_configs = []
            for m in SUPPORTED_MARKETS:
                all_configs.extend(await system_source_repo.get_enabled_configs(market=m, enabled_only=enabled_only))
            configs = all_configs

        return JSONResponse(content=configs)

    except Exception as e:
        logger.error(f"Failed to get source configs: {e}")
        raise HTTPException(
            status_code=500,
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
                status_code=404,
                detail=f"数据源配置不存在: {source_id}"
            )

        return JSONResponse(content=config)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取数据源配置失败: {str(e)}"
        )


# =============================================================================
# 用户数据源配置接口
# =============================================================================

@router.get("/user-sources/configs")
async def get_user_source_configs(
    market: Optional[str] = None,
    enabled_only: bool = True,
    current_user: UserModel = Depends(get_current_active_user),
    user_source_repo: UserDataSourceRepository = Depends(lambda: UserDataSourceRepository())
):
    """
    获取用户的数据源配置列表

    返回当前用户配置的所有数据源
    """
    try:
        user_id = str(current_user.id)
        configs = await user_source_repo.get_user_configs(
            user_id=user_id,
            market=market,
            enabled=enabled_only
        )

        return JSONResponse(content=configs)

    except Exception as e:
        logger.error(f"Failed to get user source configs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取用户数据源配置失败: {str(e)}"
        )


@router.get("/user-sources/config/{source_id}")
async def get_user_source_config(
    source_id: str,
    market: str = "A_STOCK",
    current_user: UserModel = Depends(get_current_active_user),
    user_source_repo: UserDataSourceRepository = Depends(lambda: UserDataSourceRepository())
):
    """
    获取用户单个数据源配置

    返回指定数据源的配置信息
    """
    try:
        user_id = str(current_user.id)
        config = await user_source_repo.get_config(
            user_id=user_id,
            source_id=source_id,
            market=market
        )

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"用户数据源配置不存在: {source_id}"
            )

        # 隐藏敏感信息（API Key）
        if "config" in config and "api_key" in config["config"]:
            config["config"]["api_key"] = "******"

        return JSONResponse(content=config)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user source config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取用户数据源配置失败: {str(e)}"
        )


@router.post("/user-sources/config")
async def create_user_source_config(
    request: UserSourceConfigCreate,
    current_user: UserModel = Depends(get_current_active_user),
    user_source_repo: UserDataSourceRepository = Depends(lambda: UserDataSourceRepository())
):
    """
    创建用户数据源配置

    允许用户配置自己的付费数据源（如 TuShare Pro、Alpha Vantage）
    """
    try:
        user_id = str(current_user.id)

        # 验证允许配置的数据源
        allowed_sources = {
            "A_STOCK": ["tushare_pro"],
            "US_STOCK": ["alpha_vantage"],
            "HK_STOCK": [],  # 暂不支持
        }

        if request.market not in allowed_sources:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的市场类型: {request.market}"
            )

        if request.source_id not in allowed_sources[request.market]:
            raise HTTPException(
                status_code=400,
                detail=f"不允许配置该数据源: {request.source_id}。允许的数据源: {allowed_sources[request.market]}"
            )

        # 创建配置
        from core.market_data.models.datasource import UserDataSourceConfig
        config = UserDataSourceConfig(
            user_id=user_id,
            source_id=request.source_id,
            market=request.market,
            enabled=request.enabled,
            priority=request.priority,
            config={"api_key": request.api_key}
        )

        doc_id = await user_source_repo.upsert_config(config)

        logger.info(f"Created user source config: user_id={user_id}, source_id={request.source_id}, market={request.market}")

        return JSONResponse(content={
            "message": "数据源配置创建成功",
            "doc_id": doc_id
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create user source config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"创建用户数据源配置失败: {str(e)}"
        )


@router.put("/user-sources/config/{source_id}")
async def update_user_source_config(
    source_id: str,
    market: str,
    request: UserSourceConfigUpdate,
    current_user: UserModel = Depends(get_current_active_user),
    user_source_repo: UserDataSourceRepository = Depends(lambda: UserDataSourceRepository())
):
    """
    更新用户数据源配置

    更新指定数据源的配置信息
    """
    try:
        user_id = str(current_user.id)

        # 获取现有配置
        existing_config = await user_source_repo.get_config(
            user_id=user_id,
            source_id=source_id,
            market=market
        )

        if not existing_config:
            raise HTTPException(
                status_code=404,
                detail=f"用户数据源配置不存在: {source_id}"
            )

        # 构建更新数据
        updates = {}
        if request.api_key is not None:
            updates["config"] = {**existing_config.get("config", {}), "api_key": request.api_key}
        if request.enabled is not None:
            updates["enabled"] = request.enabled
        if request.priority is not None:
            updates["priority"] = request.priority

        # 更新配置
        from core.market_data.models.datasource import UserDataSourceConfig
        updated_config = UserDataSourceConfig(
            user_id=user_id,
            source_id=source_id,
            market=market,
            enabled=request.enabled if request.enabled is not None else existing_config["enabled"],
            priority=request.priority if request.priority is not None else existing_config["priority"],
            config=updates.get("config", existing_config["config"])
        )

        doc_id = await user_source_repo.upsert_config(updated_config)

        logger.info(f"Updated user source config: user_id={user_id}, source_id={source_id}, market={market}")

        return JSONResponse(content={
            "message": "数据源配置更新成功",
            "doc_id": doc_id
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user source config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"更新用户数据源配置失败: {str(e)}"
        )


@router.delete("/user-sources/config/{source_id}")
async def delete_user_source_config(
    source_id: str,
    market: str,
    current_user: UserModel = Depends(get_current_active_user),
    user_source_repo: UserDataSourceRepository = Depends(lambda: UserDataSourceRepository())
):
    """
    删除用户数据源配置

    删除指定的数据源配置
    """
    try:
        user_id = str(current_user.id)

        deleted_count = await user_source_repo.delete_config(
            user_id=user_id,
            source_id=source_id,
            market=market
        )

        if deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"用户数据源配置不存在: {source_id}"
            )

        logger.info(f"Deleted user source config: user_id={user_id}, source_id={source_id}, market={market}")

        return JSONResponse(content={"message": "数据源配置删除成功"})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user source config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"删除用户数据源配置失败: {str(e)}"
        )


@router.post("/user-sources/config/{source_id}/test")
async def test_user_source_config(
    source_id: str,
    market: str,
    current_user: UserModel = Depends(get_current_active_user),
    user_source_repo: UserDataSourceRepository = Depends(lambda: UserDataSourceRepository())
):
    """
    测试用户数据源配置

    测试用户配置的数据源是否可用
    """
    try:
        user_id = str(current_user.id)

        config = await user_source_repo.get_config(
            user_id=user_id,
            source_id=source_id,
            market=market
        )

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"用户数据源配置不存在: {source_id}"
            )

        # 根据数据源类型测试连接
        success = False
        error = None

        try:
            if source_id == "tushare_pro":
                from core.market_data.sources.a_stock.tushare_adapter import TuShareAdapter
                adapter = TuShareAdapter(config=config["config"])
                success = await adapter.test_connection()
            elif source_id == "alpha_vantage":
                from core.market_data.sources.us_stock.alphavantage_adapter import AlphaVantageAdapter
                adapter = AlphaVantageAdapter(config=config["config"])
                success = await adapter.test_connection()
            else:
                error = f"不支持的数据源类型: {source_id}"

            if not success and not error:
                error = "连接测试失败"
        except Exception as e:
            error = str(e)

        # 更新测试状态
        status = "success" if success else "failed"
        await user_source_repo.update_test_status(
            user_id=user_id,
            source_id=source_id,
            market=market,
            status=status,
            error=error
        )

        logger.info(f"Tested user source config: user_id={user_id}, source_id={source_id}, success={success}")

        return JSONResponse(content={
            "success": success,
            "error": error,
            "test_time": datetime.now().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test user source config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"测试用户数据源配置失败: {str(e)}"
        )


# =============================================================================
# 手动触发同步接口
# =============================================================================

async def _run_full_sync_task(
    market: str,
    user_id: str
) -> None:
    """
    后台执行全量同步任务

    Args:
        market: 市场类型
        user_id: 用户ID
    """
    logger.info(f"🚀 [后台任务] 开始执行 {market} 全量同步，用户: {user_id}")
    start_time = datetime.now()

    from core.market_data.services.data_sync_service import DataSyncService
    from core.market_data.repositories.stock_info import StockInfoRepository
    from core.market_data.models import MarketType

    sync_service = DataSyncService()
    stock_repo = StockInfoRepository()
    market_type = MarketType(market.lower())

    results = {
        "market": market,
        "user_id": user_id,
        "started_at": start_time.isoformat(),
        "tasks": []
    }

    # 1. 同步股票列表
    try:
        logger.info(f"📋 [{market}] [后台任务] 开始同步股票列表...")
        stock_list_result = await sync_service.sync_stock_list_with_fallback(
            market=market_type,
            status="L"
        )
        results["tasks"].append({
            "name": "同步股票列表",
            "status": stock_list_result["status"],
            "result": stock_list_result.get("result", {})
        })
        logger.info(f"✅ [{market}] [后台任务] 股票列表同步完成: "
                   f"状态={stock_list_result['status']}, "
                   f"记录数={stock_list_result.get('result', {}).get('total', 0)}, "
                   f"数据源={stock_list_result.get('result', {}).get('source', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ [{market}] [后台任务] 股票列表同步失败: {e}")
        results["tasks"].append({
            "name": "同步股票列表",
            "status": "failed",
            "error": str(e)
        })

    # 2. 同步日线行情（最近1个月，限制前100只股票）
    try:
        logger.info(f"📈 [{market}] [后台任务] 开始同步日线行情...")
        stocks = await stock_repo.get_by_market(market_type, limit=100)
        symbols = [s["symbol"] for s in stocks]

        if symbols:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

            quotes_result = await sync_service.sync_daily_quotes_with_fallback(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )
            results["tasks"].append({
                "name": "同步日线行情",
                "status": quotes_result["status"],
                "result": quotes_result.get("result", {})
            })
            logger.info(f"✅ [{market}] [后台任务] 日线行情同步完成: "
                       f"状态={quotes_result['status']}, "
                       f"记录数={quotes_result.get('result', {}).get('total_quotes', 0)}, "
                       f"数据源={quotes_result.get('result', {}).get('source', 'unknown')}")
        else:
            logger.warning(f"⚠️ [{market}] [后台任务] 没有找到股票列表，跳过日线行情同步")
            results["tasks"].append({
                "name": "同步日线行情",
                "status": "skipped",
                "error": "没有找到股票列表"
            })
    except Exception as e:
        logger.error(f"❌ [{market}] [后台任务] 日线行情同步失败: {e}")
        results["tasks"].append({
            "name": "同步日线行情",
            "status": "failed",
            "error": str(e)
        })

    # 3. 同步公司信息（仅A股）
    if market == "A_STOCK":
        try:
            logger.info(f"🏢 [{market}] [后台任务] 开始同步公司信息...")
            stocks = await stock_repo.get_by_market(MarketType.A_STOCK, limit=50)
            symbols = [s["symbol"] for s in stocks]

            if symbols:
                company_result = await sync_service.sync_company_info_with_fallback(
                    symbols=symbols
                )
                results["tasks"].append({
                    "name": "同步公司信息",
                    "status": company_result["status"],
                    "result": company_result.get("result", {})
                })
                logger.info(f"✅ [{market}] [后台任务] 公司信息同步完成: "
                           f"状态={company_result['status']}, "
                           f"记录数={company_result.get('result', {}).get('total_records', 0)}, "
                           f"数据源={company_result.get('result', {}).get('source', 'unknown')}")
            else:
                logger.warning(f"⚠️ [{market}] [后台任务] 没有找到股票列表，跳过公司信息同步")
                results["tasks"].append({
                    "name": "同步公司信息",
                    "status": "skipped",
                    "error": "没有找到股票列表"
                })
        except Exception as e:
            logger.error(f"❌ [{market}] [后台任务] 公司信息同步失败: {e}")
            results["tasks"].append({
                "name": "同步公司信息",
                "status": "failed",
                "error": str(e)
            })

    results["finished_at"] = datetime.now().isoformat()
    results["total_tasks"] = len(results["tasks"])
    results["successful_tasks"] = sum(1 for t in results["tasks"] if t["status"] in ["completed", "completed_with_errors"])

    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"🎉 [{market}] [后台任务] 全量同步完成: "
               f"成功={results['successful_tasks']}/{results['total_tasks']}，耗时={elapsed:.2f}秒")


@router.post("/sync/trigger-full")
async def trigger_full_sync(
    market: str = Query("A_STOCK", description="市场类型: A_STOCK, US_STOCK, HK_STOCK"),
    background_tasks: BackgroundTasks = None,
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    手动触发全量同步（后台执行，不阻塞）

    触发指定市场的全量数据同步，包括：
    - 股票列表
    - 日线行情（最近1个月）
    - 公司信息
    - 财务数据

    同步任务将在后台异步执行，立即返回任务ID。
    """
    user_id = str(current_user.id)
    task_id = f"sync_{market.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    logger.info(f"📨 收到全量同步请求: 市场={market}, 用户={user_id}, 任务ID={task_id}")

    # 添加后台任务（如果传入了 background_tasks）
    if background_tasks:
        background_tasks.add_task(_run_full_sync_task, market, user_id)
        logger.info(f"✅ 同步任务已加入后台执行: 任务ID={task_id}")

        return JSONResponse(content={
            "success": True,
            "message": f"全量同步任务已提交到后台执行",
            "task_id": task_id,
            "market": market,
            "user_id": user_id,
            "submitted_at": datetime.now().isoformat()
        })
    else:
        # 如果没有传入 background_tasks，则同步执行（兼容旧逻辑）
        logger.warning(f"⚠️ 未传入 BackgroundTasks，同步执行同步任务")
        await _run_full_sync_task(market, user_id)

        return JSONResponse(content={
            "success": True,
            "message": "全量同步已完成",
            "task_id": task_id,
            "market": market,
            "user_id": user_id,
            "executed_at": datetime.now().isoformat()
        })
