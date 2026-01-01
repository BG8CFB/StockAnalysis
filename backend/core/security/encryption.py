"""
数据加密工具

使用 Fernet 对称加密保护敏感数据（如 API Key）。
"""

import os
import base64
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    加密管理器

    使用 Fernet 对称加密算法（AES-128-CBC + HMAC）。
    """

    def __init__(self):
        """初始化加密管理器"""
        # 从环境变量获取加密密钥
        encryption_key = os.getenv("API_ENCRYPTION_KEY")

        if not encryption_key:
            # 如果没有设置环境变量，生成一个密钥并警告
            # ⚠️ 生产环境必须通过环境变量设置固定密钥
            encryption_key = Fernet.generate_key().decode()
            logger.warning(
                "⚠️ 未设置 API_ENCRYPTION_KEY 环境变量！"
                "已生成临时密钥，服务器重启后将无法解密之前的数据。"
                f"请设置环境变量: API_ENCRYPTION_KEY={encryption_key}"
            )

        # 确保密钥是 32 字节的 base64 编码格式
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()

        try:
            # 验证密钥格式
            if len(encryption_key) != 44:  # Fernet 密钥固定 44 字符（base64）
                # 如果密钥长度不对，尝试从任意字符串生成
                import hashlib
                key_hash = hashlib.sha256(encryption_key).digest()
                encryption_key = base64.urlsafe_b64encode(key_hash)

            self._cipher = Fernet(encryption_key)
            self._key = encryption_key.decode()
        except Exception as e:
            logger.error(f"加密密钥初始化失败: {e}")
            raise ValueError(f"加密密钥无效: {e}")

    def encrypt(self, plaintext: str) -> str:
        """
        加密明文

        Args:
            plaintext: 明文字符串

        Returns:
            加密后的 base64 字符串
        """
        if not plaintext:
            return ""

        try:
            encrypted_bytes = self._cipher.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"加密失败: {e}")
            raise ValueError(f"加密失败: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """
        解密密文

        Args:
            ciphertext: 加密的 base64 字符串

        Returns:
            解密后的明文字符串

        Raises:
            ValueError: 解密失败或密钥错误
        """
        if not ciphertext:
            return ""

        try:
            decrypted_bytes = self._cipher.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            logger.error("解密失败: 密钥错误或数据已损坏")
            raise ValueError("解密失败: 密钥错误或数据已损坏")
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise ValueError(f"解密失败: {e}")

    def is_encrypted(self, value: str) -> bool:
        """
        检查值是否已加密

        简单的启发式检查：Fernet 加密的结果是 base64 格式
        """
        if not value:
            return False

        try:
            # 尝试 base64 解码 (Fernet 使用 urlsafe base64)
            decoded = base64.urlsafe_b64decode(value)

            # Fernet 格式: version(1) + timestamp(8) + IV(16) + ciphertext + HMAC(32)
            # 最小长度: 1 + 8 + 16 + 16 (1 block) + 32 = 73 bytes
            # 实际上只要 header 合法且长度足够就可以认为是加密的
            if len(decoded) < 57:  # 至少要有 header 和 HMAC
                return False

            # 检查版本字节 (Fernet version 0x80)
            if decoded[0] != 0x80:
                return False

            return True
        except Exception:
            return False

    @property
    def key_preview(self) -> str:
        """
        获取密钥预览（用于日志）

        只显示前 8 个字符，用于确认密钥是否正确
        """
        return self._key[:8] + "..." if self._key else ""


# =============================================================================
# 全局加密管理器实例
# =============================================================================

_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """获取全局加密管理器实例"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
        logger.info(f"加密管理器初始化成功 (密钥: {_encryption_manager.key_preview})")
    return _encryption_manager


# =============================================================================
# 便捷函数
# =============================================================================

def encrypt_sensitive_data(plaintext: str) -> str:
    """加密敏感数据"""
    return get_encryption_manager().encrypt(plaintext)


def decrypt_sensitive_data(ciphertext: str) -> str:
    """解密敏感数据"""
    return get_encryption_manager().decrypt(ciphertext)


def is_encrypted(value: str) -> bool:
    """检查值是否已加密"""
    return get_encryption_manager().is_encrypted(value)
