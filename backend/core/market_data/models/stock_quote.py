"""
股票行情数据模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class StockQuote(BaseModel):
    """日线行情数据模型 (stock_quotes)"""

    symbol: str = Field(..., description="标准化股票代码，如600000.SH")
    market: str = Field(..., description="市场类型")
    trade_date: str = Field(..., description="交易日期，格式YYYY-MM-DD")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量（股）")
    amount: Optional[float] = Field(None, description="成交额（元）")
    turnover_rate: Optional[float] = Field(None, description="换手率(%)")
    change_pct: Optional[float] = Field(None, description="涨跌幅（%）")
    pre_close: Optional[float] = Field(None, description="昨收价")
    data_source: str = Field(..., description="数据来源")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    @field_validator("trade_date")
    @classmethod
    def validate_trade_date(cls, v: str) -> str:
        """验证日期格式"""
        if not v:
            return v
        # 简单验证格式 YYYY-MM-DD
        if len(v) == 10 and v[4] == "-" and v[7] == "-":
            return v
        # 兼容 YYYYMMDD 并转换
        if len(v) == 8 and v.isdigit():
            return f"{v[:4]}-{v[4:6]}-{v[6:]}"
        raise ValueError(f"日期格式错误，应为YYYY-MM-DD：{v}")


class StockMinuteQuote(BaseModel):
    """分钟行情数据模型 (stock_minute)"""

    symbol: str = Field(..., description="股票代码")
    trade_time: Optional[str] = Field(None, description="交易时间，格式YYYY-MM-DD HH:MM:SS")
    trade_date: Optional[str] = Field(None, description="交易日期（别名）")
    market: Optional[str] = Field(None, description="市场类型")
    open: Optional[float] = Field(None, description="开盘价")
    high: Optional[float] = Field(None, description="最高价")
    low: Optional[float] = Field(None, description="最低价")
    close: Optional[float] = Field(None, description="收盘价")
    volume: Optional[float] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    data_source: str = Field(..., description="数据来源")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    @field_validator("trade_time")
    @classmethod
    def validate_trade_time(cls, v: str) -> str:
        """验证时间格式"""
        if not v:
            return v
        # 简单验证格式 YYYY-MM-DD HH:MM:SS
        if len(v) == 19 and v[4] == "-" and v[7] == "-":
            return v
        # 兼容其他格式可在此添加
        return v


class StockDailyIndicator(BaseModel):
    """每日基本面指标模型 (stock_daily_indicator)"""

    symbol: str = Field(..., description="股票代码")
    trade_date: str = Field(..., description="交易日期")
    pe: Optional[float] = Field(None, description="市盈率(总)")
    pe_ttm: Optional[float] = Field(None, description="市盈率(TTM)")
    pb: Optional[float] = Field(None, description="市净率")
    ps_ttm: Optional[float] = Field(None, description="市销率(TTM)")
    dv_ttm: Optional[float] = Field(None, description="股息率(TTM)")
    total_mv: Optional[float] = Field(None, description="总市值(万)")
    circ_mv: Optional[float] = Field(None, description="流通市值(万)")
    turnover_rate: Optional[float] = Field(None, description="换手率(%)")
    turnover_rate_f: Optional[float] = Field(None, description="自由流通换手率")
    volume_ratio: Optional[float] = Field(None, description="量比")
    data_source: str = Field(..., description="数据来源")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    @field_validator("trade_date")
    @classmethod
    def validate_trade_date(cls, v: str) -> str:
        """验证日期格式"""
        if not v:
            return v
        if len(v) == 10 and v[4] == "-" and v[7] == "-":
            return v
        if len(v) == 8 and v.isdigit():
            return f"{v[:4]}-{v[4:6]}-{v[6:]}"
        raise ValueError(f"日期格式错误，应为YYYY-MM-DD：{v}")


class MarketBoardDaily(BaseModel):
    """板块日线行情模型 (market_board_daily)"""

    board_code: str = Field(..., description="板块代码")
    board_name: str = Field(..., description="板块名称")
    trade_date: str = Field(..., description="交易日期")
    close: Optional[float] = Field(None, description="最新价")
    pct_chg: Optional[float] = Field(None, description="涨跌幅")
    turnover_rate: Optional[float] = Field(None, description="换手率")
    leading_stock: Optional[str] = Field(None, description="领涨股")
    data_source: str = Field(..., description="数据来源")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


# 别名，用于兼容性
StockKLine = StockMinuteQuote
