"""
股票基础信息模型
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator

from . import MarketType, Exchange


class StockInfo(BaseModel):
    """股票基础信息模型"""
    symbol: str = Field(..., description="股票代码，如600519.SH")
    market: MarketType = Field(..., description="市场类型")
    name: str = Field(..., description="股票名称")
    industry: Optional[str] = Field(None, description="所属行业")
    sector: Optional[str] = Field(None, description="所属板块")
    listing_date: str = Field(..., description="上市日期，格式YYYYMMDD")
    exchange: Exchange = Field(..., description="交易所代码")
    status: str = Field(default="L", description="上市状态：L上市/D退市/P暂停")
    data_source: str = Field(..., description="数据来源：tushare/akshare")

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """验证股票代码格式"""
        if '.' not in v:
            raise ValueError(f"股票代码格式错误，应包含交易所后缀：{v}")
        return v

    @field_validator('listing_date')
    @classmethod
    def validate_listing_date(cls, v: str) -> str:
        """验证日期格式"""
        if v == "" or v is None:
            return v
        if len(v) != 8 or not v.isdigit():
            raise ValueError(f"日期格式错误，应为YYYYMMDD：{v}")
        return v
