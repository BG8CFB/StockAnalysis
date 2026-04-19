"""
宏观经济数据模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MacroEconomy(BaseModel):
    """宏观经济数据模型 (macro_economy)"""

    date: str = Field(default="", description="日期，格式YYYYMMDD")
    indicator: str = Field(..., description="指标名称：gdp/cpi/ppi/pmi/shibor等")
    value: float = Field(..., description="数值")
    yoy: Optional[float] = Field(None, description="同比(%)")
    mom: Optional[float] = Field(None, description="环比(%)")
    period: Optional[str] = Field(None, description="数据周期/报告期")
    unit: Optional[str] = Field(None, description="数据单位")
    data_source: str = Field(..., description="数据来源")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


# 别名，用于兼容性
MacroEconomic = MacroEconomy
