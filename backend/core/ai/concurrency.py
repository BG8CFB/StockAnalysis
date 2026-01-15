"""
并发管理器

控制用户级和系统级的并发请求数。
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConcurrencyConfig:
    """并发配置"""
    max_user_concurrent: int = 3      # 每用户最大并发数
    max_system_concurrent: int = 50   # 系统总并发数
    queue_timeout: int = 30           # 队列超时（秒）


class ConcurrencyManager:
    """并发管理器

    控制用户级和系统级的并发请求数。
    """

    def __init__(self, config: Optional[ConcurrencyConfig] = None):
        self.config = config or ConcurrencyConfig()
        self._user_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._system_semaphore = asyncio.Semaphore(self.config.max_system_concurrent)
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self, model_config: Dict, user_id: str):
        """
        获取并发令牌（上下文管理器）

        Args:
            model_config: 模型配置
            user_id: 用户 ID

        Usage:
            async with concurrency_manager.acquire(config, user_id):
                # 执行需要并发控制的操作
                pass
        """
        # 获取用户级信号量
        user_sem = await self._get_user_semaphore(user_id)

        # 同时获取用户级和系统级令牌
        system_acquired = False
        user_acquired = False

        try:
            # 等待系统级令牌
            await asyncio.wait_for(
                self._system_semaphore.acquire(),
                timeout=self.config.queue_timeout
            )
            system_acquired = True
            logger.debug(f"系统并发令牌已获取: user={user_id}")

            # 等待用户级令牌
            await asyncio.wait_for(
                user_sem.acquire(),
                timeout=self.config.queue_timeout
            )
            user_acquired = True
            logger.debug(f"用户并发令牌已获取: user={user_id}")

            # 返回控制权给调用方
            yield

        except asyncio.TimeoutError:
            logger.warning(
                f"并发令牌获取超时: user={user_id}, "
                f"system_acquired={system_acquired}, user_acquired={user_acquired}"
            )
            raise PermissionError(
                f"并发请求过多，请稍后重试 "
                f"(用户限制: {self.config.max_user_concurrent}, "
                f"系统限制: {self.config.max_system_concurrent})"
            )

        finally:
            # 释放令牌（按相反顺序）
            if user_acquired:
                user_sem.release()
                logger.debug(f"用户并发令牌已释放: user={user_id}")
            if system_acquired:
                self._system_semaphore.release()
                logger.debug(f"系统并发令牌已释放: user={user_id}")

    async def _get_user_semaphore(self, user_id: str) -> asyncio.Semaphore:
        """获取或创建用户级信号量"""
        async with self._lock:
            if user_id not in self._user_semaphores:
                self._user_semaphores[user_id] = asyncio.Semaphore(
                    self.config.max_user_concurrent
                )
                logger.debug(
                    f"创建用户信号量: user={user_id}, "
                    f"limit={self.config.max_user_concurrent}"
                )
            return self._user_semaphores[user_id]

    def get_stats(self) -> Dict:
        """
        获取并发统计

        Returns:
            统计信息字典
        """
        return {
            "max_user_concurrent": self.config.max_user_concurrent,
            "max_system_concurrent": self.config.max_system_concurrent,
            "system_available": self._system_semaphore._value,
            "system_in_use": self.config.max_system_concurrent - self._system_semaphore._value,
            "active_users": len(self._user_semaphores),
        }

    def clear_user_semaphore(self, user_id: str):
        """
        清除用户信号量（用于用户登出等场景）

        Args:
            user_id: 用户 ID
        """
        if user_id in self._user_semaphores:
            del self._user_semaphores[user_id]
            logger.debug(f"清除用户信号量: user={user_id}")
