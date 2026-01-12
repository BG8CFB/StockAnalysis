"""
宏观经济数据模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MacroEconomic(BaseModel):
    """宏观经济数据模型"""
    indicator: str = Field(..., description="指标名称：gdp/cpi/ppi/pmi/shibor等")
    period: str = Field(..., description="统计周期，格式YYYY-Q1或YYYY-MM")
    value: float = Field(..., description="指标数值")
    unit: Optional[str] = Field(None, description="单位")
    yoy: Optional[float] = Field(None, description="同比增长率（%）")
    mom: Optional[float] = Field(None, description="环比增长率（%）")
    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")
