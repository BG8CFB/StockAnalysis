"""
股票财务数据模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from . import MarketType


class StockFinancial(BaseModel):
    """财务报表数据模型"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场类型")
    report_date: str = Field(..., description="报告期，格式YYYYMMDD")
    report_type: str = Field(..., description="报告类型：Q1/Q2/Q3/Q4/annual")
    publish_date: Optional[str] = Field(None, description="发布日期")

    # 利润表
    income_statement: Optional[dict] = Field(None, description="利润表数据")

    # 资产负债表
    balance_sheet: Optional[dict] = Field(None, description="资产负债表数据")

    # 现金流量表
    cash_flow: Optional[dict] = Field(None, description="现金流量表数据")

    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")


class StockFinancialIndicator(BaseModel):
    """财务指标数据模型"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场类型")
    report_date: str = Field(..., description="报告期，格式YYYYMMDD")
    publish_date: Optional[str] = Field(None, description="发布日期")

    # 盈利能力指标
    roe: Optional[float] = Field(None, description="净资产收益率（%）")
    roa: Optional[float] = Field(None, description="总资产净利率（%）")
    gross_profit_margin: Optional[float] = Field(None, description="销售毛利率（%）")
    net_profit_margin: Optional[float] = Field(None, description="销售净利率（%）")

    # 偿债能力指标
    debt_to_assets: Optional[float] = Field(None, description="资产负债率（%）")
    current_ratio: Optional[float] = Field(None, description="流动比率")
    quick_ratio: Optional[float] = Field(None, description="速动比率")

    # 营运能力指标
    eps: Optional[float] = Field(None, description="基本每股收益（元）")
    bps: Optional[float] = Field(None, description="每股净资产（元）")

    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")
