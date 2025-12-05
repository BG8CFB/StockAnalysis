from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel


# 用户相关事件
class UserRegisteredEvent(BaseModel):
    user_id: str
    email: str
    username: str
    timestamp: datetime = datetime.utcnow()


class UserLoginEvent(BaseModel):
    user_id: str
    email: str
    timestamp: datetime = datetime.utcnow()


class UserLogoutEvent(BaseModel):
    user_id: str
    timestamp: datetime = datetime.utcnow()


# 模块相关事件
class ModuleLoadedEvent(BaseModel):
    module_name: str
    module_version: str = "1.0.0"
    timestamp: datetime = datetime.utcnow()


class ModuleErrorEvent(BaseModel):
    module_name: str
    error_message: str
    error_type: str
    timestamp: datetime = datetime.utcnow()


# 系统相关事件
class SystemStartupEvent(BaseModel):
    startup_time: datetime = datetime.utcnow()
    modules_loaded: list[str] = []


class SystemShutdownEvent(BaseModel):
    shutdown_time: datetime = datetime.utcnow()
    reason: str = "manual"


# 事件类型常量
class EventTypes:
    # 用户事件
    USER_REGISTERED = "user.registered"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_UPDATED = "user.updated"

    # 模块事件
    MODULE_LOADED = "module.loaded"
    MODULE_ERROR = "module.error"
    MODULE_UNLOADED = "module.unloaded"

    # 系统事件
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"

    # 认证事件
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILED = "auth.failed"
    TOKEN_EXPIRED = "auth.token_expired"

    # 数据事件
    DATA_CREATED = "data.created"
    DATA_UPDATED = "data.updated"
    DATA_DELETED = "data.deleted"