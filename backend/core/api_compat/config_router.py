"""
配置管理兼容路由

为前端 /api/config/* 端点提供统一入口。
包含系统配置、LLM 厂家/模型、数据源、数据库、市场分类、模型目录、导入导出等全部端点。
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.ai.model_catalog_models import (
    ModelCatalogCreateRequest,
)
from core.ai.model_catalog_service import get_model_catalog_service
from core.ai.provider_models import (
    LLMProviderCreateRequest,
    LLMProviderToggleRequest,
    LLMProviderUpdateRequest,
)
from core.ai.provider_service import get_llm_provider_service
from core.auth.dependencies import get_current_active_user
from core.db.mongodb import mongodb
from core.market_data.category_models import (
    DataSourceGroupingCreateRequest,
    DataSourceOrderRequest,
    MarketCategoryCreateRequest,
)
from core.market_data.category_service import get_market_category_service
from core.user.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["配置管理"])


# =============================================================================
# 辅助函数
# =============================================================================


def _success(data: Any = None, message: str = "操作成功") -> Dict:
    """构造统一成功响应"""
    return {"success": True, "data": data, "message": message}


def _error(message: str, code: int = 400) -> HTTPException:
    """构造统一错误响应"""
    return HTTPException(status_code=code, detail=message)


# =============================================================================
# Group 1: 系统配置 (2)
# =============================================================================


@router.post("/reload")
async def reload_config(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """重新加载配置"""
    # 清除 Redis 缓存中的系统配置
    from core.db.redis import get_redis

    redis = await get_redis()
    await redis.delete("system:config")
    return _success(
        {"reloaded_at": datetime.now(timezone.utc).isoformat()},
        "配置已重新加载",
    )


@router.get("/system")
async def get_system_config(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取完整系统配置"""
    db = mongodb.database

    # 聚合各子系统的配置
    llm_configs = await db.ai_model_configs.find(
        {"enabled": True},
        {"_id": 0, "api_key": 0},
    ).to_list(length=None)

    default_llm_doc = await db.system_config.find_one({"key": "default_llm"})
    default_llm = default_llm_doc.get("value", "") if default_llm_doc else ""

    # 数据源配置
    from core.market_data.repositories.datasource import SystemDataSourceRepository

    ds_repo = SystemDataSourceRepository()
    ds_configs_raw = await ds_repo.find_many({})
    data_source_configs = []
    for ds in ds_configs_raw:
        ds.pop("_id", None)
        ds.pop("api_key", None)
        data_source_configs.append(ds)

    default_ds_doc = await db.system_config.find_one({"key": "default_data_source"})
    default_data_source = default_ds_doc.get("value", "akshare") if default_ds_doc else "akshare"

    # 数据库配置
    db_configs_raw = await db.database_configs.find({}).to_list(length=None)
    database_configs = []
    for dc in db_configs_raw:
        dc["name"] = dc.get("name", "")
        dc.pop("_id", None)
        if dc.get("password"):
            dc["password"] = "****"
        database_configs.append(dc)

    # 系统设置
    from core.settings.services.system_service import settings_service

    system_settings = await settings_service.get_system_config()

    return _success(
        {
            "config_name": "system",
            "config_type": "full",
            "llm_configs": llm_configs,
            "default_llm": default_llm,
            "data_source_configs": data_source_configs,
            "default_data_source": default_data_source,
            "database_configs": database_configs,
            "system_settings": system_settings,
        }
    )


# =============================================================================
# Group 2: LLM 厂家管理 (11)
# =============================================================================


@router.get("/llm/providers")
async def get_llm_providers(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取所有 LLM 厂家"""
    service = get_llm_provider_service()
    providers = await service.list_providers()
    return _success(providers)


@router.post("/llm/providers")
async def add_llm_provider(
    data: LLMProviderCreateRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """添加 LLM 厂家"""
    service = get_llm_provider_service()
    try:
        provider_id = await service.create_provider(data)
        return _success({"id": provider_id}, "厂家已添加")
    except ValueError as e:
        raise _error(str(e), 409)


@router.put("/llm/providers/{provider_id}")
async def update_llm_provider(
    provider_id: str,
    data: LLMProviderUpdateRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """更新 LLM 厂家"""
    service = get_llm_provider_service()
    await service.update_provider(provider_id, data)
    return _success(None, "厂家已更新")


@router.delete("/llm/providers/{provider_id}")
async def delete_llm_provider(
    provider_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """删除 LLM 厂家"""
    service = get_llm_provider_service()
    await service.delete_provider(provider_id)
    return _success(None, "厂家已删除")


@router.patch("/llm/providers/{provider_id}/toggle")
async def toggle_llm_provider(
    provider_id: str,
    data: LLMProviderToggleRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """启用/禁用 LLM 厂家"""
    service = get_llm_provider_service()
    await service.toggle_provider(provider_id, data.is_active)
    return _success(None, "厂家状态已更新")


@router.post("/llm/providers/{provider_id}/test")
async def test_llm_provider(
    provider_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """测试厂家 API 连接"""
    service = get_llm_provider_service()
    result = await service.test_connection(provider_id)
    return _success(result)


@router.post("/llm/providers/{provider_id}/fetch-models")
async def fetch_llm_provider_models(
    provider_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """从厂家 API 拉取模型列表"""
    service = get_llm_provider_service()
    result = await service.fetch_models(provider_id)
    return _success(result)


@router.post("/llm/providers/migrate-env")
async def migrate_env_to_providers(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """将环境变量配置迁移到厂家管理"""
    service = get_llm_provider_service()
    result = await service.migrate_from_env()
    return _success(result)


@router.post("/llm/providers/init-aggregators")
async def init_aggregator_providers(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """初始化聚合渠道厂家"""
    service = get_llm_provider_service()
    result = await service.init_aggregators()
    return _success(result)


# =============================================================================
# Group 3: LLM 模型配置 (4)
# =============================================================================


@router.get("/llm")
async def get_llm_configs(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取所有 LLM 模型配置"""
    db = mongodb.database
    # 只返回启用的模型
    cursor = db.ai_model_configs.find({"enabled": True}, {"api_key": 0})
    configs = await cursor.to_list(length=None)

    results = []
    for cfg in configs:
        cfg.pop("_id", None)
        # 适配前端 LLMConfig 字段
        results.append(
            {
                "provider": cfg.get("platform_name", cfg.get("provider", "custom")),
                "model_name": cfg.get("model_id", ""),
                "model_display_name": cfg.get("name", ""),
                "api_base": cfg.get("api_base_url", ""),
                "max_tokens": cfg.get("max_concurrency", 40),
                "temperature": cfg.get("temperature", 0.5),
                "timeout": cfg.get("timeout_seconds", 60),
                "retry_times": 3,
                "enabled": cfg.get("enabled", True),
                "description": cfg.get("description"),
            }
        )
    return _success(results)


class LLMConfigRequest(BaseModel):
    """LLM 模型配置请求"""

    provider: str
    model_name: str
    model_display_name: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    timeout: Optional[int] = None
    retry_times: Optional[int] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None


@router.post("/llm")
async def add_or_update_llm_config(
    data: LLMConfigRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """添加/更新 LLM 模型配置"""
    from core.security.encryption import encrypt_sensitive_data

    db = mongodb.database
    # 使用 provider + model_name 作为唯一键
    existing = await db.ai_model_configs.find_one(
        {
            "provider": data.provider,
            "model_id": data.model_name,
        }
    )

    if existing:
        # 更新
        update_fields: Dict[str, Any] = {}
        if data.model_display_name is not None:
            update_fields["name"] = data.model_display_name
        if data.api_key is not None:
            update_fields["api_key"] = encrypt_sensitive_data(data.api_key)
        if data.api_base is not None:
            update_fields["api_base_url"] = data.api_base
        if data.max_tokens is not None:
            update_fields["max_concurrency"] = data.max_tokens
        if data.temperature is not None:
            update_fields["temperature"] = data.temperature
        if data.timeout is not None:
            update_fields["timeout_seconds"] = data.timeout
        if data.enabled is not None:
            update_fields["enabled"] = data.enabled
        if data.description is not None:
            update_fields["description"] = data.description

        if update_fields:
            update_fields["updated_at"] = datetime.now(timezone.utc)
            await db.ai_model_configs.update_one(
                {"_id": existing["_id"]},
                {"$set": update_fields},
            )
        return _success({"message": "模型配置已更新", "model_name": data.model_name})
    else:
        # 创建
        from core.ai.model.schemas import PlatformTypeEnum

        doc: Dict[str, Any] = {
            "name": data.model_display_name or data.model_name,
            "platform_type": PlatformTypeEnum.CUSTOM.value,
            "platform_name": None,
            "provider": data.provider,
            "api_base_url": data.api_base or "",
            "api_key": encrypt_sensitive_data(data.api_key) if data.api_key else "",
            "model_id": data.model_name,
            "custom_headers": {},
            "max_concurrency": data.max_tokens or 40,
            "task_concurrency": 2,
            "batch_concurrency": 1,
            "timeout_seconds": data.timeout or 60,
            "temperature": data.temperature or 0.5,
            "enabled": data.enabled if data.enabled is not None else True,
            "thinking_enabled": False,
            "is_system": False,
            "owner_id": str(current_user.id),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        await db.ai_model_configs.insert_one(doc)
        return _success({"message": "模型配置已创建", "model_name": data.model_name})


@router.delete("/llm/{provider}/{model_name}")
async def delete_llm_config(
    provider: str,
    model_name: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """删除 LLM 模型配置"""
    db = mongodb.database
    result = await db.ai_model_configs.delete_one(
        {
            "provider": provider,
            "model_id": model_name,
        }
    )
    if result.deleted_count == 0:
        raise _error("模型配置不存在", 404)
    return _success({"message": "模型配置已删除"})


class SetDefaultRequest(BaseModel):
    """设置默认请求"""

    name: str


@router.post("/llm/set-default")
async def set_default_llm(
    data: SetDefaultRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """设置默认分析大模型"""
    db = mongodb.database
    await db.system_config.update_one(
        {"key": "default_llm"},
        {
            "$set": {
                "value": data.name,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    return _success({"message": "默认模型已设置", "default_llm": data.name})


# =============================================================================
# Group 4: 数据源配置 (5)
# =============================================================================


@router.get("/datasource")
async def get_datasource_configs(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取所有数据源配置"""
    db = mongodb.database
    configs = await db.config_datasources.find({}).to_list(length=None)
    for c in configs:
        c.pop("_id", None)
        if c.get("api_key"):
            c["api_key"] = "****"
        if c.get("api_secret"):
            c["api_secret"] = "****"
    return _success(configs)


class DataSourceConfigRequest(BaseModel):
    """数据源配置请求"""

    name: str
    type: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    endpoint: Optional[str] = None
    timeout: Optional[int] = None
    rate_limit: Optional[int] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    config_params: Optional[Dict] = None
    description: Optional[str] = None
    market_categories: Optional[List[str]] = None
    display_name: Optional[str] = None
    provider: Optional[str] = None


@router.post("/datasource")
async def add_datasource_config(
    data: DataSourceConfigRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """添加数据源配置"""
    db = mongodb.database
    existing = await db.config_datasources.find_one({"name": data.name})
    if existing:
        raise _error(f"数据源 '{data.name}' 已存在", 409)

    from core.security.encryption import encrypt_sensitive_data

    doc = data.model_dump(exclude_none=True)
    if data.api_key:
        doc["api_key"] = encrypt_sensitive_data(data.api_key)
    if data.api_secret:
        doc["api_secret"] = encrypt_sensitive_data(data.api_secret)
    doc["created_at"] = datetime.now(timezone.utc)

    await db.config_datasources.insert_one(doc)
    return _success({"message": "数据源已添加", "name": data.name})


@router.put("/datasource/{name}")
async def update_datasource_config(
    name: str,
    data: DataSourceConfigRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """更新数据源配置"""
    db = mongodb.database
    update_fields: Dict[str, Any] = {}
    for field_name in [
        "type",
        "endpoint",
        "timeout",
        "rate_limit",
        "enabled",
        "priority",
        "config_params",
        "description",
        "market_categories",
        "display_name",
        "provider",
    ]:
        val = getattr(data, field_name, None)
        if val is not None:
            update_fields[field_name] = val

    if data.api_key is not None:
        from core.security.encryption import encrypt_sensitive_data

        update_fields["api_key"] = encrypt_sensitive_data(data.api_key)
    if data.api_secret is not None:
        from core.security.encryption import encrypt_sensitive_data

        update_fields["api_secret"] = encrypt_sensitive_data(data.api_secret)

    result = await db.config_datasources.update_one(
        {"name": name},
        {"$set": update_fields},
    )
    if result.matched_count == 0:
        raise _error("数据源不存在", 404)
    return _success({"message": "数据源已更新"})


@router.delete("/datasource/{name}")
async def delete_datasource_config(
    name: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """删除数据源配置"""
    db = mongodb.database
    result = await db.config_datasources.delete_one({"name": name})
    if result.deleted_count == 0:
        raise _error("数据源不存在", 404)
    return _success({"message": "数据源已删除"})


@router.post("/datasource/set-default")
async def set_default_datasource(
    data: SetDefaultRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """设置默认数据源"""
    db = mongodb.database
    await db.system_config.update_one(
        {"key": "default_data_source"},
        {
            "$set": {
                "value": data.name,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    return _success({"message": "默认数据源已设置", "default_data_source": data.name})


# =============================================================================
# Group 5: 数据库配置 (7)
# =============================================================================


class DatabaseConfigRequest(BaseModel):
    """数据库配置请求"""

    name: str
    type: str
    host: str = "localhost"
    port: int = 27017
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    connection_params: Optional[Dict] = None
    pool_size: Optional[int] = None
    max_overflow: Optional[int] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None


@router.get("/database")
async def get_database_configs(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取所有数据库配置"""
    db = mongodb.database
    configs = await db.database_configs.find({}).to_list(length=None)
    for c in configs:
        c.pop("_id", None)
        if c.get("password"):
            c["password"] = "****"
    return _success(configs)


@router.get("/database/{db_name}")
async def get_database_config(
    db_name: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取指定数据库配置"""
    db = mongodb.database
    config = await db.database_configs.find_one({"name": db_name})
    if not config:
        raise _error("数据库配置不存在", 404)
    config.pop("_id", None)
    if config.get("password"):
        config["password"] = "****"
    return _success(config)


@router.post("/database")
async def add_database_config(
    data: DatabaseConfigRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """添加数据库配置"""
    db = mongodb.database
    existing = await db.database_configs.find_one({"name": data.name})
    if existing:
        raise _error(f"数据库配置 '{data.name}' 已存在", 409)

    from core.security.encryption import encrypt_sensitive_data

    doc = data.model_dump(exclude_none=True)
    if data.password:
        doc["password"] = encrypt_sensitive_data(data.password)
    doc["created_at"] = datetime.now(timezone.utc)

    await db.database_configs.insert_one(doc)
    return _success({"success": True, "message": "数据库配置已添加"})


@router.put("/database/{db_name}")
async def update_database_config(
    db_name: str,
    data: DatabaseConfigRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """更新数据库配置"""
    db = mongodb.database
    update_fields: Dict[str, Any] = {}
    for field_name in [
        "type",
        "host",
        "port",
        "username",
        "database",
        "connection_params",
        "pool_size",
        "max_overflow",
        "enabled",
        "description",
    ]:
        val = getattr(data, field_name, None)
        if val is not None:
            update_fields[field_name] = val

    if data.password is not None:
        from core.security.encryption import encrypt_sensitive_data

        update_fields["password"] = encrypt_sensitive_data(data.password)

    result = await db.database_configs.update_one(
        {"name": db_name},
        {"$set": update_fields},
    )
    if result.matched_count == 0:
        raise _error("数据库配置不存在", 404)
    return _success({"success": True, "message": "数据库配置已更新"})


@router.delete("/database/{db_name}")
async def delete_database_config(
    db_name: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """删除数据库配置"""
    db = mongodb.database
    result = await db.database_configs.delete_one({"name": db_name})
    if result.deleted_count == 0:
        raise _error("数据库配置不存在", 404)
    return _success({"success": True, "message": "数据库配置已删除"})


@router.post("/database/{db_name}/test")
async def test_database_config(
    db_name: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """测试数据库连接"""
    db = mongodb.database
    config = await db.database_configs.find_one({"name": db_name})
    if not config:
        raise _error("数据库配置不存在", 404)

    # 解密密码
    password = config.get("password", "")
    if password:
        try:
            from core.security.encryption import decrypt_sensitive_data, is_encrypted

            if is_encrypted(password):
                password = decrypt_sensitive_data(password)
        except Exception:
            pass

    db_type = config.get("type", "mongodb")
    start_time = time.time()

    try:
        if db_type == "mongodb":
            # 简单的连接测试：通过当前 MongoDB 实例判断
            await mongodb.database.client.admin.command("ping")
            elapsed = int((time.time() - start_time) * 1000)
            return _success(
                {
                    "success": True,
                    "message": "MongoDB 连接成功",
                    "response_time": elapsed,
                }
            )
        elif db_type == "redis":
            from core.db.redis import get_redis

            redis = await get_redis()
            await redis.ping()
            elapsed = int((time.time() - start_time) * 1000)
            return _success(
                {
                    "success": True,
                    "message": "Redis 连接成功",
                    "response_time": elapsed,
                }
            )
        else:
            return _success(
                {
                    "success": False,
                    "message": f"暂不支持测试 {db_type} 类型数据库",
                }
            )
    except Exception as e:
        elapsed = int((time.time() - start_time) * 1000)
        return _success(
            {
                "success": False,
                "message": f"连接失败: {str(e)}",
                "response_time": elapsed,
            }
        )


# =============================================================================
# Group 6: 通用配置测试 (1)
# =============================================================================


class ConfigTestRequest(BaseModel):
    """通用配置测试请求"""

    config_type: str
    config_data: Dict[str, Any]


@router.post("/test")
async def test_config(
    data: ConfigTestRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """通用配置连接测试"""
    import httpx

    config_type = data.config_type
    config_data = data.config_data
    start_time = time.time()

    try:
        if config_type == "llm":
            base_url = config_data.get("api_base_url", config_data.get("api_base", ""))
            api_key = config_data.get("api_key", "")
            if not base_url or not api_key:
                raise _error("缺少 api_base_url 或 api_key")

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{base_url.rstrip('/')}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                elapsed = int((time.time() - start_time) * 1000)
                return _success(
                    {
                        "success": resp.status_code == 200,
                        "message": f"状态码 {resp.status_code}",
                        "response_time": elapsed,
                    }
                )

        elif config_type == "database":
            db_type = config_data.get("type", "mongodb")
            if db_type == "mongodb":
                await mongodb.database.client.admin.command("ping")
            elif db_type == "redis":
                from core.db.redis import get_redis

                redis = await get_redis()
                await redis.ping()
            elapsed = int((time.time() - start_time) * 1000)
            return _success(
                {
                    "success": True,
                    "message": "连接成功",
                    "response_time": elapsed,
                }
            )

        elif config_type == "datasource":
            endpoint = config_data.get("endpoint", "")
            api_key = config_data.get("api_key", "")
            if not endpoint:
                raise _error("缺少 endpoint")
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(endpoint, headers=headers)
                elapsed = int((time.time() - start_time) * 1000)
                return _success(
                    {
                        "success": resp.status_code < 400,
                        "message": f"状态码 {resp.status_code}",
                        "response_time": elapsed,
                    }
                )

        else:
            raise _error(f"不支持的配置类型: {config_type}")

    except HTTPException:
        raise
    except Exception as e:
        elapsed = int((time.time() - start_time) * 1000)
        return _success(
            {
                "success": False,
                "message": f"测试失败: {str(e)}",
                "response_time": elapsed,
            }
        )


# =============================================================================
# Group 7: 市场分类 (4)
# =============================================================================


@router.get("/market-categories")
async def get_market_categories(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取所有市场分类"""
    service = get_market_category_service()
    categories = await service.list_categories()
    return _success(categories)


@router.post("/market-categories")
async def add_market_category(
    data: MarketCategoryCreateRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """添加市场分类"""
    service = get_market_category_service()
    try:
        category_id = await service.create_category(data)
        return _success({"message": "分类已添加", "id": category_id})
    except ValueError as e:
        raise _error(str(e), 409)


@router.put("/market-categories/{category_id}")
async def update_market_category(
    category_id: str,
    data: Dict[str, Any],
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """更新市场分类"""
    service = get_market_category_service()
    await service.update_category(category_id, data)
    return _success({"message": "分类已更新"})


@router.delete("/market-categories/{category_id}")
async def delete_market_category(
    category_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """删除市场分类"""
    service = get_market_category_service()
    await service.delete_category(category_id)
    return _success({"message": "分类已删除"})


# =============================================================================
# Group 8: 数据源分组 (5)
# =============================================================================


@router.get("/datasource-groupings")
async def get_datasource_groupings(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取所有数据源分组"""
    service = get_market_category_service()
    groupings = await service.list_groupings()
    return _success(groupings)


@router.post("/datasource-groupings")
async def add_datasource_to_category(
    data: DataSourceGroupingCreateRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """将数据源添加到分类"""
    service = get_market_category_service()
    try:
        await service.add_grouping(data)
        return _success({"message": "分组已添加"})
    except ValueError as e:
        raise _error(str(e), 409)


@router.delete("/datasource-groupings/{data_source_name}/{category_id}")
async def remove_datasource_from_category(
    data_source_name: str,
    category_id: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """从分类中移除数据源"""
    service = get_market_category_service()
    await service.remove_grouping(data_source_name, category_id)
    return _success({"message": "分组已移除"})


@router.put("/datasource-groupings/{data_source_name}/{category_id}")
async def update_datasource_grouping(
    data_source_name: str,
    category_id: str,
    data: Dict[str, Any],
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """更新数据源分组"""
    service = get_market_category_service()
    await service.update_grouping(data_source_name, category_id, data)
    return _success({"message": "分组已更新"})


@router.put("/market-categories/{category_id}/datasource-order")
async def update_category_datasource_order(
    category_id: str,
    data: DataSourceOrderRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """更新分类内数据源排序"""
    service = get_market_category_service()
    await service.reorder_datasources(category_id, data.data_sources)
    return _success({"message": "排序已更新"})


# =============================================================================
# Group 9: 系统设置 (3)
# =============================================================================


@router.get("/settings")
async def get_system_settings(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取系统设置"""
    from core.settings.services.system_service import settings_service

    config = await settings_service.get_system_config()
    return _success(config)


@router.get("/settings/meta")
async def get_system_settings_meta(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取系统设置元数据"""
    # 构造设置元数据
    import os

    items = []

    env_keys = [
        ("ZHIPU_API_KEY", True, True, "env"),
        ("ZHIPU_API_BASE", False, True, "env"),
        ("ZHIPU_MODEL", False, True, "env"),
        ("MONGODB_URL", False, False, "env"),
        ("REDIS_URL", False, False, "env"),
        ("SECRET_KEY", True, False, "env"),
        ("CORS_ORIGINS", False, True, "env"),
        ("DEBUG", False, True, "env"),
        ("LOG_LEVEL", False, True, "env"),
        ("REQUIRE_APPROVAL", False, True, "env"),
        ("ENABLE_REGISTRATION", False, True, "db"),
    ]

    for key, sensitive, editable, source in env_keys:
        items.append(
            {
                "key": key,
                "sensitive": sensitive,
                "editable": editable,
                "source": source,
                "has_value": bool(os.getenv(key, "")),
            }
        )

    return {
        "success": True,
        "data": {"items": items},
        "message": "获取设置元数据成功",
    }


@router.put("/settings")
async def update_system_settings(
    settings_data: Dict[str, Any],
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """更新系统设置"""
    from core.settings.services.system_service import settings_service

    await settings_service.update_system_config(settings_data, str(current_user.id))
    return _success({"message": "系统设置已更新"})


# =============================================================================
# Group 10: 模型目录 (6)
# =============================================================================


@router.get("/model-catalog")
async def get_model_catalogs(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取所有模型目录"""
    service = get_model_catalog_service()
    catalogs = await service.list_catalogs()
    return _success(catalogs)


@router.get("/model-catalog/{provider}")
async def get_provider_model_catalog(
    provider: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取指定厂家模型目录"""
    service = get_model_catalog_service()
    catalog = await service.get_catalog(provider)
    if not catalog:
        raise _error("模型目录不存在", 404)
    return _success(catalog)


@router.post("/model-catalog")
async def save_model_catalog(
    data: ModelCatalogCreateRequest,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """保存模型目录"""
    service = get_model_catalog_service()
    await service.save_catalog(data)
    return _success({"success": True, "message": "模型目录已保存"})


@router.delete("/model-catalog/{provider}")
async def delete_model_catalog(
    provider: str,
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """删除模型目录"""
    service = get_model_catalog_service()
    await service.delete_catalog(provider)
    return _success({"success": True, "message": "模型目录已删除"})


@router.post("/model-catalog/init")
async def init_model_catalog(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """初始化默认模型目录"""
    service = get_model_catalog_service()
    result = await service.init_defaults()
    return _success(result)


@router.get("/models")
async def get_available_models(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取可用模型列表"""
    service = get_model_catalog_service()
    models = await service.get_available_models()
    return _success(models)


# =============================================================================
# Group 11: 导入导出 (3)
# =============================================================================


@router.post("/export")
async def export_config(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """导出完整配置"""
    db = mongodb.database

    export_data: Dict[str, Any] = {}

    # AI 模型配置（脱敏）
    ai_configs = await db.ai_model_configs.find({}, {"api_key": 0}).to_list(length=None)
    for c in ai_configs:
        c.pop("_id", None)
    export_data["ai_model_configs"] = ai_configs

    # 数据源配置（脱敏）
    ds_configs = await db.config_datasources.find({}).to_list(length=None)
    for c in ds_configs:
        c.pop("_id", None)
        c.pop("api_key", None)
    export_data["datasource_configs"] = ds_configs

    # 数据库配置（脱敏）
    db_configs = await db.database_configs.find({}).to_list(length=None)
    for c in db_configs:
        c.pop("_id", None)
        c.pop("password", None)
    export_data["database_configs"] = db_configs

    # 市场分类
    categories = await db.market_categories.find({}).to_list(length=None)
    for c in categories:
        c.pop("_id", None)
    export_data["market_categories"] = categories

    # 数据源分组
    groupings = await db.datasource_groupings.find({}).to_list(length=None)
    for g in groupings:
        g.pop("_id", None)
    export_data["datasource_groupings"] = groupings

    # 模型目录
    catalogs = await db.model_catalog.find({}).to_list(length=None)
    for c in catalogs:
        c.pop("_id", None)
    export_data["model_catalogs"] = catalogs

    # LLM 厂家
    providers = await db.llm_providers.find({}, {"api_key": 0, "api_secret": 0}).to_list(
        length=None
    )
    for p in providers:
        p.pop("_id", None)
    export_data["llm_providers"] = providers

    return _success(
        {
            "message": "配置导出成功",
            "data": export_data,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@router.post("/import")
async def import_config(
    config_data: Dict[str, Any],
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """导入配置"""
    db = mongodb.database
    imported_count = 0

    collection_map = {
        "ai_model_configs": "ai_model_configs",
        "datasource_configs": "config_datasources",
        "database_configs": "database_configs",
        "market_categories": "market_categories",
        "datasource_groupings": "datasource_groupings",
        "model_catalogs": "model_catalog",
        "llm_providers": "llm_providers",
    }

    for key, collection_name in collection_map.items():
        items = config_data.get(key, [])
        if not items:
            continue
        collection = db[collection_name]
        for item in items:
            item.pop("_id", None)
            try:
                await collection.insert_one(item)
                imported_count += 1
            except Exception:
                # 跳过重复或无效数据
                pass

    return _success({"message": f"导入完成，共导入 {imported_count} 条配置"})


@router.post("/migrate-legacy")
async def migrate_legacy_config(
    current_user: UserModel = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """迁移传统配置格式"""
    db = mongodb.database

    migrated_count = 0

    # 迁移旧的 AI 模型配置（如果 provider 字段不存在但 platform_name 存在）
    legacy_configs = await db.ai_model_configs.find(
        {
            "provider": {"$exists": False},
            "platform_name": {"$exists": True},
        }
    ).to_list(length=None)

    for cfg in legacy_configs:
        platform_name = cfg.get("platform_name", "custom")
        await db.ai_model_configs.update_one(
            {"_id": cfg["_id"]},
            {"$set": {"provider": platform_name}},
        )
        migrated_count += 1

    return _success({"message": f"迁移完成，共迁移 {migrated_count} 条配置"})
