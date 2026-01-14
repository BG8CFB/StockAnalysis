"""
数据编码工具

使用 Base64 编码保护敏感数据（如 API Key）。
适用于开发/自部署场景，无密钥管理，永不"过期"。

注意：Base64 仅编码，非加密。生产环境如需真加密，请使用 Fernet。
"""

import base64
import logging

logger = logging.getLogger(__name__)


class EncodingManager:
    """
    编码管理器（使用 Base64）
    """

    def encrypt(self, plaintext: str) -> str:
        """
        编码明文（Base64）

        Args:
            plaintext: 明文字符串

        Returns:
            Base64 编码后的字符串
        """
        if not plaintext:
            return ""
        try:
            encoded = base64.b64encode(plaintext.encode('utf-8')).decode('utf-8')
            return encoded
        except Exception as e:
            logger.error(f"编码失败: {e}")
            raise ValueError(f"编码失败: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """
        解码密文（Base64）

        Args:
            ciphertext: Base64 编码的字符串

        Returns:
            解码后的明文字符串
        """
        if not ciphertext:
            return ""
        try:
            decoded = base64.b64decode(ciphertext.encode('utf-8')).decode('utf-8')
            return decoded
        except Exception as e:
            logger.error(f"解码失败: {e}")
            raise ValueError(f"解码失败: {e}")

    def is_encrypted(self, value: str) -> bool:
        """
        检查值是否是 Base64 编码格式

        简单检查：是否为有效的 Base64 字符串
        """
        if not value:
            return False
        try:
            # 尝试解码，成功则为 Base64
            decoded = base64.b64decode(value.encode('utf-8'))
            # 检查解码后的内容是否为可打印 UTF-8
            decoded.decode('utf-8')
            return True
        except Exception:
            return False

    @property
    def key_preview(self) -> str:
        """获取密钥预览（Base64 无密钥）"""
        return "Base64编码(无密钥)"


# =============================================================================
# 全局编码管理器实例
# =============================================================================

_encoding_manager: EncodingManager = None


def get_encoding_manager() -> EncodingManager:
    """获取全局编码管理器实例"""
    global _encoding_manager
    if _encoding_manager is None:
        _encoding_manager = EncodingManager()
        logger.info("✅ 编码管理器初始化成功 (Base64)")
    return _encoding_manager


# =============================================================================
# 便捷函数
# =============================================================================

def encrypt_sensitive_data(plaintext: str) -> str:
    """编码敏感数据（Base64）"""
    return get_encoding_manager().encrypt(plaintext)


def decrypt_sensitive_data(ciphertext: str) -> str:
    """解码敏感数据（Base64）"""
    return get_encoding_manager().decrypt(ciphertext)


def is_encrypted(value: str) -> bool:
    """检查值是否是 Base64 编码"""
    return get_encoding_manager().is_encrypted(value)
