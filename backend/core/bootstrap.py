import importlib
import importlib.util
import os
import logging
from typing import Dict, List, Any
from pathlib import Path
from fastapi import FastAPI, APIRouter
from pydantic import BaseModel

from ..db.mongodb import mongodb
from ..events.bus import event_bus
from ..events.schemas import EventTypes, ModuleLoadedEvent, ModuleErrorEvent

logger = logging.getLogger(__name__)


class ModuleInfo(BaseModel):
    """模块信息"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    router_prefix: str = ""
    enabled: bool = True
    dependencies: List[str] = []


class ModuleLoader:
    """模块加载器 - 核心插件系统"""

    def __init__(self):
        self.loaded_modules: Dict[str, Any] = {}
        self.module_info: Dict[str, ModuleInfo] = {}
        self.modules_path = Path(__file__).parent.parent / "modules"

    async def load_modules(self, app: FastAPI):
        """自动加载所有模块"""
        logger.info("Starting module loading process...")

        # 扫描modules目录
        if not self.modules_path.exists():
            logger.warning(f"Modules directory not found: {self.modules_path}")
            return

        for module_dir in self.modules_path.iterdir():
            if module_dir.is_dir() and not module_dir.name.startswith("__"):
                await self._load_module(app, module_dir.name)

        # 发布系统启动事件
        await event_bus.publish(
            EventTypes.SYSTEM_STARTUP,
            {"modules_loaded": list(self.loaded_modules.keys())}
        )

        logger.info(f"Module loading completed. Loaded modules: {list(self.loaded_modules.keys())}")

    async def _load_module(self, app: FastAPI, module_name: str):
        """加载单个模块"""
        try:
            logger.info(f"Loading module: {module_name}")

            # 检查模块是否包含必要文件
            module_path = self.modules_path / module_name
            init_file = module_path / "__init__.py"
            api_file = module_path / "api.py"

            if not init_file.exists():
                logger.warning(f"Module {module_name} missing __init__.py, skipping...")
                return

            # 动态导入模块
            spec = importlib.util.spec_from_file_location(
                f"modules.{module_name}",
                init_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 获取模块信息
            module_info = getattr(module, "MODULE_INFO", ModuleInfo(name=module_name))
            self.module_info[module_name] = module_info

            # 注册API路由
            if api_file.exists():
                api_spec = importlib.util.spec_from_file_location(
                    f"modules.{module_name}.api",
                    api_file
                )
                api_module = importlib.util.module_from_spec(api_spec)
                api_spec.loader.exec_module(api_module)

                # 获取APIRouter
                if hasattr(api_module, "router"):
                    router = api_module.router
                    prefix = module_info.router_prefix or f"/api/{module_name}"
                    app.include_router(router, prefix=prefix)
                    logger.info(f"Registered API routes for {module_name} with prefix {prefix}")

            # 注册数据库模型（如果有的话）
            if hasattr(module, "register_models"):
                await module.register_models(mongodb)
                logger.info(f"Registered database models for {module_name}")

            # 初始化模块（如果有的话）
            if hasattr(module, "initialize"):
                await module.initialize()
                logger.info(f"Initialized module {module_name}")

            # 订阅模块事件（如果有的话）
            if hasattr(module, "subscribe_events"):
                await module.subscribe_events(event_bus)
                logger.info(f"Subscribed to events for {module_name}")

            self.loaded_modules[module_name] = module

            # 发布模块加载事件
            await event_bus.publish(
                EventTypes.MODULE_LOADED,
                {
                    "module_name": module_name,
                    "module_version": module_info.version
                },
                source_module="core"
            )

            logger.info(f"Successfully loaded module: {module_name}")

        except Exception as e:
            logger.error(f"Failed to load module {module_name}: {e}")
            # 发布模块错误事件
            await event_bus.publish(
                EventTypes.MODULE_ERROR,
                {
                    "module_name": module_name,
                    "error_message": str(e),
                    "error_type": type(e).__name__
                },
                source_module="core"
            )

    async def unload_module(self, module_name: str):
        """卸载模块"""
        if module_name in self.loaded_modules:
            try:
                module = self.loaded_modules[module_name]

                # 清理模块（如果有的话）
                if hasattr(module, "cleanup"):
                    await module.cleanup()
                    logger.info(f"Cleaned up module {module_name}")

                # 从loaded_modules中移除
                del self.loaded_modules[module_name]
                if module_name in self.module_info:
                    del self.module_info[module_name]

                # 发布模块卸载事件
                await event_bus.publish(
                    EventTypes.MODULE_UNLOADED,
                    {"module_name": module_name},
                    source_module="core"
                )

                logger.info(f"Successfully unloaded module: {module_name}")

            except Exception as e:
                logger.error(f"Failed to unload module {module_name}: {e}")

    def get_loaded_modules(self) -> List[str]:
        """获取已加载的模块列表"""
        return list(self.loaded_modules.keys())

    def get_module_info(self, module_name: str) -> ModuleInfo:
        """获取模块信息"""
        return self.module_info.get(module_name)

    def is_module_loaded(self, module_name: str) -> bool:
        """检查模块是否已加载"""
        return module_name in self.loaded_modules


# 全局模块加载器实例
module_loader = ModuleLoader()