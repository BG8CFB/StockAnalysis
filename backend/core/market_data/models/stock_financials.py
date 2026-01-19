"""
股票财务数据模型
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from . import MarketType


class StockFinancial(BaseModel):
    """综合财务报表模型 (stock_financials)

    用于存储利润表、资产负债表、现金流量表的统一财务报表数据。
    不同类型的财务数据通过 report_type 字段区分。
    """
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场类型")
    report_date: str = Field(..., description="报告期，格式YYYYMMDD")
    report_type: str = Field(..., description="报告类型：income利润表/balance资产负债表/cashflow现金流量表")
    publish_date: Optional[str] = Field(None, description="发布日期")
    income_statement: Optional[Dict[str, Any]] = Field(None, description="利润表数据")
    balance_sheet: Optional[Dict[str, Any]] = Field(None, description="资产负债表数据")
    cash_flow: Optional[Dict[str, Any]] = Field(None, description="现金流量表数据")
    data_source: str = Field(..., description="数据来源")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class FinancialIncome(BaseModel):
    """利润表模型 (financial_income)"""
    symbol: str = Field(..., description="股票代码")
    end_date: str = Field(..., description="报告期，格式YYYYMMDD")
    ann_date: Optional[str] = Field(None, description="公告日期")
    revenue: Optional[float] = Field(None, description="营业收入")
    op_income: Optional[float] = Field(None, description="营业利润")
    net_profit: Optional[float] = Field(None, description="净利润")
    basic_eps: Optional[float] = Field(None, description="基本每股收益")
    data_source: str = Field(..., description="数据来源")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class FinancialBalance(BaseModel):
    """资产负债表模型 (financial_balance)"""
    symbol: str = Field(..., description="股票代码")
    end_date: str = Field(..., description="报告期，格式YYYYMMDD")
    ann_date: Optional[str] = Field(None, description="公告日期")
    total_assets: Optional[float] = Field(None, description="资产总计")
    total_liab: Optional[float] = Field(None, description="负债合计")
    total_share: Optional[float] = Field(None, description="期末总股本")
    data_source: str = Field(..., description="数据来源")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class FinancialCashFlow(BaseModel):
    """现金流量表模型 (financial_cashflow)"""
    symbol: str = Field(..., description="股票代码")
    end_date: str = Field(..., description="报告期，格式YYYYMMDD")
    ann_date: Optional[str] = Field(None, description="公告日期")
    net_cash_flows_oper_act: Optional[float] = Field(None, description="经营活动产生的现金流量净额")
    net_cash_flows_inv_act: Optional[float] = Field(None, description="投资活动产生的现金流量净额")
    net_cash_flows_fnc_act: Optional[float] = Field(None, description="筹资活动产生的现金流量净额")
    data_source: str = Field(..., description="数据来源")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class StockFinancialIndicator(BaseModel):
    """财务指标数据模型 (financial_indicator)"""
    symbol: str = Field(..., description="股票代码")
    end_date: str = Field(..., description="报告期，格式YYYYMMDD")
    ann_date: Optional[str] = Field(None, description="公告日期")
    eps: Optional[float] = Field(None, description="基本每股收益")
    bps: Optional[float] = Field(None, description="每股净资产")
    roe: Optional[float] = Field(None, description="净资产收益率(%)")
    roa: Optional[float] = Field(None, description="总资产收益率(%)")
    gross_margin: Optional[float] = Field(None, description="毛利率(%)")
    net_margin: Optional[float] = Field(None, description="净利率(%)")
    current_ratio: Optional[float] = Field(None, description="流动比率")
    quick_ratio: Optional[float] = Field(None, description="速动比率")
    debt_to_assets: Optional[float] = Field(None, description="资产负债率(%)")
    data_source: str = Field(..., description="数据来源")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

