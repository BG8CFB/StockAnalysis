"""
股票基础信息模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from . import MarketType, Exchange


class StockInfo(BaseModel):
    """股票基础信息模型"""
    symbol: str = Field(..., description="标准化股票代码 (主键)，如600000.SH")
    code: str = Field(..., description="原始代码，如600000")
    market: MarketType = Field(..., description="市场类型")
    name: str = Field(..., description="股票名称")
    area: Optional[str] = Field(None, description="地域")
    industry: Optional[str] = Field(None, description="所属行业")
    fullname: Optional[str] = Field(None, description="公司全称")
    enname: Optional[str] = Field(None, description="英文名称")
    description: Optional[str] = Field(None, description="公司介绍")
    list_date: str = Field(..., description="上市日期，格式YYYYMMDD")
    list_status: str = Field(default="L", description="上市状态：L上市/D退市/P暂停")
    exchange: Exchange = Field(..., description="交易所代码")
    is_hs: Optional[str] = Field(None, description="是否沪深港通标的，N否 H沪股通 S深股通")
    data_source: str = Field(..., description="数据来源：tushare/akshare")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """验证标准化代码格式"""
        if '.' not in v:
            raise ValueError(f"标准化代码格式错误，应包含交易所后缀：{v}")
        return v

    @field_validator('list_date')
    @classmethod
    def validate_list_date(cls, v: str) -> str:
        """验证日期格式"""
        if v == "" or v is None:
            return v
        if len(v) != 8 or not v.isdigit():
            raise ValueError(f"日期格式错误，应为YYYYMMDD：{v}")
        return v


class TradeCalendar(BaseModel):
    """交易日历模型"""
    cal_date: str = Field(..., description="日历日期，格式YYYYMMDD")
    exchange: Exchange = Field(..., description="交易所")
    is_open: int = Field(..., description="是否交易 0休市 1交易")
    pretrade_date: Optional[str] = Field(None, description="上一个交易日")
    data_source: str = Field(..., description="数据来源")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
