"""配置初始化"""

import os
from typing import Optional

from pydantic import BaseModel

from core.config import settings


class MarketDataConfig(BaseModel):
    """市场数据模块配置"""

    # TuShare配置
    tushare_token: str

    # 数据保留策略
    daily_quotes_retention_days: int = 7  # 日线行情保留天数
    minute_quotes_retention_days: int = 7  # 分钟行情保留天数
    financials_retention_months: int = 12  # 财务数据保留月数

    # 降级配置
    max_failure_count: int = 3  # 最大失败次数
    enable_fallback: bool = True  # 是否启用降级

    @classmethod
    def from_env(cls) -> "MarketDataConfig":
        """从环境变量加载配置"""
        tushare_token = settings.TUSHARE_TOKEN

        if not tushare_token:
            raise ValueError("TUSHARE_TOKEN environment variable is required")

        return cls(
            tushare_token=tushare_token,
            daily_quotes_retention_days=int(os.getenv("DAILY_QUOTES_RETENTION_DAYS", "7")),
            minute_quotes_retention_days=int(os.getenv("MINUTE_QUOTES_RETENTION_DAYS", "7")),
            financials_retention_months=int(os.getenv("FINANCIALS_RETENTION_MONTHS", "12")),
            max_failure_count=int(os.getenv("MAX_FAILURE_COUNT", "3")),
            enable_fallback=os.getenv("ENABLE_FALLBACK", "true").lower() == "true",
        )


# 全局配置实例
_config: Optional[MarketDataConfig] = None


def get_config() -> MarketDataConfig:
    """获取配置实例"""
    global _config
    if _config is None:
        _config = MarketDataConfig.from_env()
    return _config


def set_config(config: MarketDataConfig) -> None:
    """设置配置"""
    global _config
    _config = config
