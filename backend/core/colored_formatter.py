"""
彩色日志格式器

为不同日志级别添加颜色和符号标识，提高日志可读性
"""
import logging
import sys
from typing import Optional

# 尝试导入 colorama (Windows 支持)
try:
    import colorama
    colorama.init()
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False


class ColoredFormatter(logging.Formatter):
    """带颜色和符号的日志格式器"""

    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",      # 青色
        "INFO": "\033[32m",       # 绿色
        "WARNING": "\033[33m",     # 黄色
        "ERROR": "\033[31m",      # 红色
        "CRITICAL": "\033[35m",    # 紫色
        "RESET": "\033[0m",       # 重置
    }

    # 日志级别符号
    SYMBOLS = {
        "DEBUG": "🔍",
        "INFO": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "🚨",
    }

    # Windows 系统不支持 ANSI 颜色，使用备选符号
    SYMBOLS_WINDOWS = {
        "DEBUG": "[D]",
        "INFO": "[I]",
        "WARNING": "[W]",
        "ERROR": "[E]",
        "CRITICAL": "[C]",
    }

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, use_color: bool = True):
        """
        初始化格式器

        Args:
            fmt: 日志格式字符串
            datefmt: 日期格式
            use_color: 是否使用颜色
        """
        super().__init__(fmt, datefmt)
        self.use_color = use_color and self._supports_color()

    def _supports_color(self) -> bool:
        """检查终端是否支持颜色"""
        if sys.platform == "win32":
            return HAS_COLORAMA
        return True

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        levelname = record.levelname
        levelno = record.levelno

        # 获取符号
        if self.use_color:
            symbol = self.SYMBOLS.get(levelname, "")
        else:
            symbol = self.SYMBOLS_WINDOWS.get(levelname, "")

        # 获取颜色
        color = self.COLORS.get(levelname, "")
        reset = self.COLORS["RESET"]

        # 添加颜色和符号到 levelname
        if self.use_color:
            colored_levelname = f"{color}{levelname}{reset}"
            colored_symbol = f"{color}{symbol}{reset}"
        else:
            colored_levelname = levelname
            colored_symbol = symbol

        # 保存原始 levelname
        original_levelname = record.levelname

        # 使用自定义的带符号的 levelname
        record.levelname = f"{colored_symbol} {colored_levelname}"

        # 格式化日志
        result = super().format(record)

        # 恢复原始 levelname
        record.levelname = original_levelname

        return result


class SimplifiedColoredFormatter(ColoredFormatter):
    """简化的彩色格式器，用于生产环境

    格式: [时间] [符号] [级别] 模块 | 消息
    """

    def __init__(self, use_color: bool = True):
        fmt = "%(asctime)s | %(levelname)-15s | %(name)-20s | %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        super().__init__(fmt, datefmt, use_color)


class VerboseColoredFormatter(ColoredFormatter):
    """详细的彩色格式器，用于开发环境

    格式: [时间] [符号] [级别] 模块 | 函数:行号 | 消息
    """

    def __init__(self, use_color: bool = True):
        fmt = "%(asctime)s | %(levelname)-15s | %(name)-30s | %(funcName)s:%(lineno)d | %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        super().__init__(fmt, datefmt, use_color)


def get_formatter(debug_mode: bool = True) -> ColoredFormatter:
    """
    根据模式获取合适的格式器

    Args:
        debug_mode: 是否为调试模式

    Returns:
        日志格式器实例
    """
    if debug_mode:
        return VerboseColoredFormatter(use_color=True)
    else:
        return SimplifiedColoredFormatter(use_color=True)
