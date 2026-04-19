"""
股票其他数据模型（板块、龙虎榜、分红、融资融券、新闻等）
"""

from datetime import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field


class StockMoneyFlow(BaseModel):
    """资金流向模型 (stock_money_flow)"""

    symbol: str = Field(..., description="股票代码")
    trade_date: str = Field(..., description="交易日期")
    buy_sm_vol: Optional[float] = Field(None, description="小单买入量")
    net_mf_vol: Optional[float] = Field(None, description="净流入量")
    data_source: str = Field(..., description="数据来源")
    updated_at: dt = Field(default_factory=dt.now, description="更新时间")


class StockHSGTMoneyFlow(BaseModel):
    """沪深港通资金模型 (stock_money_flow_hsgt)"""

    trade_date: str = Field(..., description="交易日期")
    north_money: Optional[float] = Field(None, description="北向资金净流入(百万元)")
    south_money: Optional[float] = Field(None, description="南向资金净流入(百万元)")
    hgt: Optional[float] = Field(None, description="沪股通净流入")
    sgt: Optional[float] = Field(None, description="深股通净流入")
    data_source: str = Field(..., description="数据来源")
    updated_at: dt = Field(default_factory=dt.now, description="更新时间")


class StockTopList(BaseModel):
    """龙虎榜数据模型 (market_top_list)"""

    symbol: str = Field(..., description="股票代码")
    trade_date: str = Field(..., description="上榜日期")
    name: Optional[str] = Field(None, description="股票名称")
    close: Optional[float] = Field(None, description="收盘价")
    pct_chg: Optional[float] = Field(None, description="涨跌幅")
    net_amount: Optional[float] = Field(None, description="净买入额")
    buy_amount: Optional[float] = Field(None, description="买入额")
    sell_amount: Optional[float] = Field(None, description="卖出额")
    reason: Optional[str] = Field(None, description="上榜原因")
    data_source: str = Field(..., description="数据来源")
    updated_at: dt = Field(default_factory=dt.now, description="更新时间")


class StockDividend(BaseModel):
    """分红配送模型 (stock_dividend)"""

    symbol: str = Field(..., description="股票代码")
    end_date: str = Field(..., description="分红年度/报告期")
    dividend_year: Optional[str] = Field(None, description="分红年度")
    ann_date: Optional[str] = Field(None, description="公告日期")
    stk_div: Optional[float] = Field(None, description="送转股比例")
    cash_div: Optional[float] = Field(None, description="派息比例")
    cash_dividend: Optional[float] = Field(None, description="派息比例（别名）")
    ex_date: Optional[str] = Field(None, description="除权除息日")
    ex_dividend_date: Optional[str] = Field(None, description="除权除息日（别名）")
    record_date: Optional[str] = Field(None, description="股权登记日")
    dividend_ratio: Optional[float] = Field(None, description="分红比例")
    data_source: str = Field(..., description="数据来源")
    updated_at: dt = Field(default_factory=dt.now, description="更新时间")


class StockMargin(BaseModel):
    """融资融券模型 (stock_margin)"""

    symbol: str = Field(..., description="股票代码")
    trade_date: str = Field(..., description="交易日期")
    rzye: Optional[float] = Field(None, description="融资余额")
    rzmre: Optional[float] = Field(None, description="融资买入额")
    rqyl: Optional[float] = Field(None, description="融券余量")
    rqye: Optional[float] = Field(None, description="融券余额")
    margin_buy: Optional[float] = Field(None, description="融资买入额（别名）")
    margin_sell: Optional[float] = Field(None, description="融资卖出额")
    margin_balance: Optional[float] = Field(None, description="融资余额（别名）")
    short_sell: Optional[float] = Field(None, description="融券卖出量")
    short_buy: Optional[float] = Field(None, description="融券买入量")
    short_balance: Optional[float] = Field(None, description="融券余额（别名）")
    data_source: str = Field(..., description="数据来源")
    updated_at: dt = Field(default_factory=dt.now, description="更新时间")


class MarketNews(BaseModel):
    """市场新闻模型 (market_news)"""

    news_id: str = Field(..., description="唯一ID")
    symbol: Optional[str] = Field(None, description="关联股票")
    ts_code: Optional[str] = Field(None, description="TuShare代码")
    datetime: str = Field(..., description="发布时间")
    title: str = Field(..., description="标题")
    content: Optional[str] = Field(None, description="内容")
    source: Optional[str] = Field(None, description="来源")
    channels: Optional[str] = Field(None, description="新闻渠道")
    data_source: str = Field(..., description="数据来源")
    updated_at: dt = Field(default_factory=dt.now, description="更新时间")
