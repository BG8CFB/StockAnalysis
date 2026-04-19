"""
邮箱验证码服务
支持发送和验证邮箱验证码（预留接口）
"""

import json
import secrets
from typing import Optional, Tuple

from core.config import settings
from core.db.redis import get_redis


class EmailVerificationService:
    """邮箱验证码服务

    预留接口，方便后期接入邮件服务
    """

    # 验证码长度
    CODE_LENGTH = 6
    # 验证码过期时间（秒）
    CODE_EXPIRE = 300  # 5 分钟

    def __init__(self) -> None:
        pass

    def _get_key(self, email: str, code_id: str) -> str:
        """获取验证码 Redis Key"""
        return f"email_code:{email}:{code_id}"

    def _get_rate_limit_key(self, email: str) -> str:
        """获取频率限制 Key"""
        return f"email_code:rate_limit:{email}"

    def _get_cooldown_key(self, email: str) -> str:
        """获取冷却时间 Key"""
        return f"email_code:cooldown:{email}"

    async def can_send_code(self, email: str) -> Tuple[bool, Optional[str]]:
        """检查是否可以发送验证码

        Args:
            email: 邮箱地址

        Returns:
            (是否可以发送, 错误信息)
        """
        redis = await get_redis()
        cooldown_key = self._get_cooldown_key(email)

        # 检查冷却时间（60秒）
        cooldown = await redis.get(cooldown_key)
        if cooldown:
            remaining = int(cooldown)
            return False, f"请等待 {remaining} 秒后再试"

        return True, None

    async def generate_code(
        self,
        email: str,
        code_type: str = "verification",
    ) -> dict:
        """生成验证码

        Args:
            email: 邮箱地址
            code_type: 验证码类型 (verification, reset, etc.)

        Returns:
            {
                "code_id": "验证码 ID",
                "code": "6位数字验证码",
                "expires_in": 300  # 过期时间（秒）
            }
        """
        # 检查频率限制
        can_send, error = await self.can_send_code(email)
        if not can_send:
            raise ValueError(error)

        # 生成验证码 ID 和验证码
        code_id = secrets.token_urlsafe(16)
        code = "".join([str(secrets.randbelow(10)) for _ in range(self.CODE_LENGTH)])

        # 存储验证码数据
        redis = await get_redis()
        key = self._get_key(email, code_id)
        code_data = {
            "code": code,
            "type": code_type,
            "created_at": __import__("time").time(),
        }
        await redis.set(
            key,
            json.dumps(code_data),
            ex=self.CODE_EXPIRE,
        )

        # 设置冷却时间（60秒）
        cooldown_key = self._get_cooldown_key(email)
        await redis.set(cooldown_key, "60", ex=60)

        return {
            "code_id": code_id,
            "code": code,
            "expires_in": self.CODE_EXPIRE,
        }

    async def send_code(
        self,
        email: str,
        code_type: str = "verification",
    ) -> dict:
        """发送验证码

        Args:
            email: 邮箱地址
            code_type: 验证码类型

        Returns:
            {
                "code_id": "验证码 ID",
                "expires_in": 300
            }
        """
        # 生成验证码
        result = await self.generate_code(email, code_type)

        # TODO: 实际发送邮件
        # 这里预留接口，方便后期接入邮件服务
        # 可以使用 SMTP、SendGrid、阿里云邮件服务等
        # 示例：
        # await self._send_email(
        #     to=email,
        #     subject="验证码",
        #     body=f"您的验证码是: {result['code']}, 5分钟内有效。"
        # )

        if settings.DEBUG:
            # 开发环境在控制台打印验证码
            print(f"[Email Code] To: {email}, Code: {result['code']}")

        # 返回结果（不包含验证码本身）
        return {
            "code_id": result["code_id"],
            "expires_in": result["expires_in"],
        }

    async def verify_code(
        self,
        email: str,
        code_id: str,
        code: str,
    ) -> bool:
        """验证验证码

        Args:
            email: 邮箱地址
            code_id: 验证码 ID
            code: 用户输入的验证码

        Returns:
            是否验证成功
        """
        redis = await get_redis()
        key = self._get_key(email, code_id)

        # 获取验证码数据
        data_str = await redis.get(key)
        if not data_str:
            return False

        code_data = json.loads(data_str)

        # 验证码匹配
        if code_data["code"] == code:
            # 验证成功，删除验证码
            await redis.delete(key)
            return True

        return False

    async def _send_email(self, to: str, subject: str, body: str) -> None:
        """发送邮件（预留方法）

        Args:
            to: 收件人邮箱
            subject: 邮件主题
            body: 邮件正文
        """
        # TODO: 实现邮件发送逻辑
        # 可以使用以下方式之一：
        # 1. Python smtplib + SMTP
        # 2. SendGrid API
        # 3. 阿里云邮件推送
        # 4. 腾讯云邮件服务
        pass


# 全局邮箱验证服务实例
_email_verification_service: Optional[EmailVerificationService] = None


def get_email_verification_service() -> EmailVerificationService:
    """获取邮箱验证服务单例"""
    global _email_verification_service
    if _email_verification_service is None:
        _email_verification_service = EmailVerificationService()
    return _email_verification_service
