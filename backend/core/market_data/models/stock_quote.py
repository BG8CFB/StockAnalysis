"""
股票行情数据模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from . import MarketType


class StockQuote(BaseModel):
    """日线行情数据模型（当日）"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场类型")
    trade_date: str = Field(..., description="交易日期，格式YYYYMMDD")
    open: float = Field(..., ge=0, description="开盘价")
    high: float = Field(..., ge=0, description="最高价")
    low: float = Field(..., ge=0, description="最低价")
    close: float = Field(..., ge=0, description="收盘价")
    pre_close: Optional[float] = Field(None, description="昨收价")
    volume: int = Field(..., ge=0, description="成交量（手）")
    amount: Optional[float] = Field(None, description="成交额（万元）")
    change: Optional[float] = Field(None, description="涨跌额")
    change_pct: Optional[float] = Field(None, description="涨跌幅（%）")
    turnover_rate: Optional[float] = Field(None, description="换手率（%）")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")

    @field_validator('trade_date')
    @classmethod
    def validate_trade_date(cls, v: str) -> str:
        """验证日期格式"""
        if v == "" or v is None:
            return v
        if len(v) != 8 or not v.isdigit():
            raise ValueError(f"日期格式错误，应为YYYYMMDD：{v}")
        return v


class StockKLine(BaseModel):
    """历史K线数据模型（包含技术指标）"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场类型")
    trade_date: str = Field(..., description="交易日期，格式YYYYMMDD")
    open: float = Field(..., ge=0, description="开盘价")
    high: float = Field(..., ge=0, description="最高价")
    low: float = Field(..., ge=0, description="最低价")
    close: float = Field(..., ge=0, description="收盘价")
    volume: int = Field(..., ge=0, description="成交量（股）")
    amount: Optional[float] = Field(None, description="成交额（万元）")
    pre_close: Optional[float] = Field(None, description="昨收价")
    change: Optional[float] = Field(None, description="涨跌额")
    change_pct: Optional[float] = Field(None, description="涨跌幅（%）")

    # 技术指标
    indicators: Optional[dict] = Field(None, description="技术指标（MA、MACD、RSI等）")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")
