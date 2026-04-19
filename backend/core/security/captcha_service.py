"""
图形验证码服务
生成和验证滑动拼图验证码
"""

import json
import secrets
from typing import Optional

from core.db.redis import get_redis


class CaptchaService:
    """图形验证码服务

    采用滑动拼图验证码：
    1. 生成验证码 token 和拼图位置
    2. 前端完成滑动后提交验证
    3. 后端验证滑动位置是否正确

    注意：这里实现的是简化版本，实际生产环境建议使用成熟的验证码服务
    """

    # 验证码过期时间（秒）
    CAPTCHA_EXPIRE = 300  # 5 分钟
    # 允许的误差范围（像素）
    TOLERANCE = 5

    def __init__(self) -> None:
        pass

    def _get_key(self, token: str) -> str:
        """获取验证码 Redis Key"""
        return f"captcha:token:{token}"

    async def generate_captcha(self) -> dict:
        """生成验证码

        Returns:
            {
                "token": "验证码 token",
                "image_url": "拼图背景图 URL（预留）",
                "puzzle_position": {"x": 100, "y": 50}  # 拼图位置（前端需要滑动的目标位置）
            }
        """
        # 生成随机 token
        token = secrets.token_urlsafe(32)

        # 生成随机拼图位置（实际项目中应该从背景图计算得出）
        # 这里简化为固定范围的随机值
        import random

        puzzle_x = random.randint(100, 250)
        puzzle_y = random.randint(50, 150)

        captcha_data = {
            "puzzle_x": puzzle_x,
            "puzzle_y": puzzle_y,
            "verified": False,
            "created_at": __import__("time").time(),
        }

        # 存储到 Redis
        redis = await get_redis()
        key = self._get_key(token)
        await redis.set(
            key,
            json.dumps(captcha_data),
            ex=self.CAPTCHA_EXPIRE,
        )

        return {
            "token": token,
            # 实际项目中应该返回拼图背景图
            # 这里返回占位符，前端可根据此生成图形验证码
            "puzzle_position": {
                "x": puzzle_x,
                "y": puzzle_y,
            },
        }

    async def verify_captcha(
        self,
        token: str,
        slide_x: int,
        slide_y: int,
    ) -> bool:
        """验证滑动拼图

        Args:
            token: 验证码 token
            slide_x: 滑块 X 坐标
            slide_y: 滑块 Y 坐标

        Returns:
            是否验证成功
        """
        redis = await get_redis()
        key = self._get_key(token)

        # 获取验证码数据
        data_str = await redis.get(key)
        if not data_str:
            return False

        captcha_data = json.loads(data_str)

        # 检查是否已验证过
        if captcha_data.get("verified"):
            # 验证码已使用，删除
            await redis.delete(key)
            return False

        # 验证位置是否在误差范围内
        puzzle_x = captcha_data["puzzle_x"]
        puzzle_y = captcha_data["puzzle_y"]

        x_valid = abs(slide_x - puzzle_x) <= self.TOLERANCE
        y_valid = abs(slide_y - puzzle_y) <= self.TOLERANCE

        if x_valid and y_valid:
            # 验证成功，标记为已使用
            captcha_data["verified"] = True
            await redis.set(
                key,
                json.dumps(captcha_data),
                ex=self.CAPTCHA_EXPIRE,
            )
            return True

        # 验证失败，删除验证码
        await redis.delete(key)
        return False

    async def is_captcha_used(self, token: str) -> bool:
        """检查验证码是否已使用

        Args:
            token: 验证码 token

        Returns:
            是否已使用
        """
        redis = await get_redis()
        key = self._get_key(token)
        data_str = await redis.get(key)
        if not data_str:
            return True  # 不存在或已过期视为已使用

        captcha_data = json.loads(data_str)
        return bool(captcha_data.get("verified", False))

    async def mark_captcha_used(self, token: str) -> None:
        """标记验证码为已使用（用于登录成功后）"""
        redis = await get_redis()
        key = self._get_key(token)
        data_str = await redis.get(key)
        if data_str:
            captcha_data = json.loads(data_str)
            captcha_data["verified"] = True
            await redis.set(
                key,
                json.dumps(captcha_data),
                ex=self.CAPTCHA_EXPIRE,
            )


# 全局验证码服务实例
_captcha_service: Optional[CaptchaService] = None


def get_captcha_service() -> CaptchaService:
    """获取验证码服务单例"""
    global _captcha_service
    if _captcha_service is None:
        _captcha_service = CaptchaService()
    return _captcha_service
