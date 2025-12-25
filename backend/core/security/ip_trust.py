"""
IP 信任管理
管理用户常用 IP，实现无感登录
"""
from typing import Optional, Set

from core.db.redis import get_redis


class IPTrustManager:
    """IP 信任管理器

    功能：
    1. 记录用户登录成功的 IP
    2. 当某 IP 登录成功次数达到阈值后，标记为信任 IP
    3. 信任 IP 登录时无需验证码
    """

    # 配置常量
    TRUSTED_THRESHOLD = 5  # 成功登录 5 次后标记为信任
    TRUSTED_EXPIRE_DAYS = 30  # 信任记录 30 天过期

    def __init__(self):
        pass

    def _get_trusted_ips_key(self, user_id: str) -> str:
        """获取用户信任 IP 集合的 Redis Key"""
        return f"ip_trust:user:{user_id}:trusted_ips"

    def _get_login_count_key(self, user_id: str, ip: str) -> str:
        """获取 IP 登录计数 Key"""
        return f"ip_trust:user:{user_id}:ip:{ip}:logins"

    async def record_login_success(self, user_id: str, ip: str) -> None:
        """记录登录成功

        Args:
            user_id: 用户 ID
            ip: 客户端 IP
        """
        redis = await get_redis()

        # 增加该 IP 的登录计数
        count_key = self._get_login_count_key(user_id, ip)
        count = await redis.incr(count_key)

        # 设置过期时间
        expire_seconds = self.TRUSTED_EXPIRE_DAYS * 24 * 3600
        await redis.expire(count_key, expire_seconds)

        # 如果达到阈值，添加到信任 IP 集合
        if count >= self.TRUSTED_THRESHOLD:
            trusted_key = self._get_trusted_ips_key(user_id)
            await redis.sadd(trusted_key, ip)
            await redis.expire(trusted_key, expire_seconds)

    async def is_ip_trusted(self, user_id: str, ip: str) -> bool:
        """检查 IP 是否为信任 IP

        Args:
            user_id: 用户 ID
            ip: 客户端 IP

        Returns:
            是否为信任 IP
        """
        redis = await get_redis()
        trusted_key = self._get_trusted_ips_key(user_id)
        is_member = await redis.sismember(trusted_key, ip)
        return bool(is_member)

    async def get_trusted_ips(self, user_id: str) -> Set[str]:
        """获取用户的所有信任 IP

        Args:
            user_id: 用户 ID

        Returns:
            信任 IP 集合
        """
        redis = await get_redis()
        trusted_key = self._get_trusted_ips_key(user_id)
        members = await redis.smembers(trusted_key)
        return set(members) if members else set()

    async def remove_trusted_ip(self, user_id: str, ip: str) -> None:
        """移除信任 IP

        Args:
            user_id: 用户 ID
            ip: 要移除的 IP
        """
        redis = await get_redis()
        trusted_key = self._get_trusted_ips_key(user_id)
        await redis.srem(trusted_key, ip)

    async def get_login_count(self, user_id: str, ip: str) -> int:
        """获取 IP 的登录次数

        Args:
            user_id: 用户 ID
            ip: 客户端 IP

        Returns:
            登录次数
        """
        redis = await get_redis()
        count_key = self._get_login_count_key(user_id, ip)
        count = await redis.get(count_key)
        return int(count) if count else 0

    async def revoke_ip_trust(self, user_id: str, ip: str = None) -> None:
        """撤销 IP 信任

        Args:
            user_id: 用户 ID
            ip: 要撤销的 IP，如果为 None 则撤销所有
        """
        redis = await get_redis()

        if ip:
            # 移除指定 IP
            await self.remove_trusted_ip(user_id, ip)
            # 重置登录计数
            count_key = self._get_login_count_key(user_id, ip)
            await redis.delete(count_key)
        else:
            # 移除所有信任 IP
            trusted_key = self._get_trusted_ips_key(user_id)
            trusted_ips = await self.get_trusted_ips(user_id)
            await redis.delete(trusted_key)
            # 重置所有相关计数
            for trusted_ip in trusted_ips:
                count_key = self._get_login_count_key(user_id, trusted_ip)
                await redis.delete(count_key)


# 全局 IP 信任管理器实例
_ip_trust_manager: Optional[IPTrustManager] = None


def get_ip_trust_manager() -> IPTrustManager:
    """获取 IP 信任管理器单例"""
    global _ip_trust_manager
    if _ip_trust_manager is None:
        _ip_trust_manager = IPTrustManager()
    return _ip_trust_manager
