"""
股票其他数据模型（板块、龙虎榜、分红、融资融券、新闻等）
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from . import MarketType


class StockSector(BaseModel):
    """板块数据模型"""
    sector_name: str = Field(..., description="板块名称")
    sector_code: str = Field(..., description="板块代码")
    sector_type: str = Field(..., description="板块类型：concept/industry")
    stock_count: Optional[int] = Field(None, description="包含股票数量")
    description: Optional[str] = Field(None, description="板块描述")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class StockTopList(BaseModel):
    """龙虎榜数据模型"""
    symbol: str = Field(..., description="股票代码")
    trade_date: str = Field(..., description="交易日期")
    close_price: Optional[float] = Field(None, description="收盘价")
    change_pct: Optional[float] = Field(None, description="涨跌幅")
    buy_total: Optional[float] = Field(None, description="买入总额（万元）")
    sell_total: Optional[float] = Field(None, description="卖出总额（万元）")
    net_buy: Optional[float] = Field(None, description="净买入额（万元）")
    reason: Optional[str] = Field(None, description="上榜原因")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class StockDividend(BaseModel):
    """分红数据模型"""
    symbol: str = Field(..., description="股票代码")
    dividend_year: str = Field(..., description="分红年度")
    ex_dividend_date: Optional[str] = Field(None, description="除权除息日")
    record_date: Optional[str] = Field(None, description="股权登记日")
    cash_dividend: Optional[float] = Field(None, description="每股现金分红（元）")
    dividend_ratio: Optional[float] = Field(None, description="分红率（%）")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class StockMargin(BaseModel):
    """融资融券数据模型"""
    symbol: str = Field(..., description="股票代码")
    trade_date: str = Field(..., description="交易日期")
    margin_buy: Optional[float] = Field(None, description="融资买入额（万元）")
    margin_sell: Optional[float] = Field(None, description="融资偿还额（万元）")
    margin_balance: Optional[float] = Field(None, description="融资余额（万元）")
    short_sell: Optional[float] = Field(None, description="融券卖出量（股）")
    short_buy: Optional[float] = Field(None, description="融券买入量（股）")
    short_balance: Optional[float] = Field(None, description="融券余额（万元）")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class StockNews(BaseModel):
    """股票新闻数据模型"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场类型")
    title: str = Field(..., description="新闻标题")
    url: str = Field(..., description="新闻链接")
    publish_time: str = Field(..., description="发布时间")
    content: str = Field(default="", description="新闻内容")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")
