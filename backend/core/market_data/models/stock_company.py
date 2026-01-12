"""
股票公司信息模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from . import MarketType


class StockCompany(BaseModel):
    """公司详细信息模型"""
    symbol: str = Field(..., description="股票代码")
    market: MarketType = Field(..., description="市场类型")
    company_name: str = Field(..., description="公司名称")
    company_name_en: Optional[str] = Field(None, description="英文名称")
    industry: Optional[str] = Field(None, description="所属行业")
    sector: Optional[str] = Field(None, description="所属板块")
    listing_date: str = Field(..., description="上市日期")

    # 联系方式
    contact: Optional[dict] = Field(None, description="联系方式")

    # 业务描述
    business: Optional[dict] = Field(None, description="业务描述")

    # 股本结构
    capital_structure: Optional[dict] = Field(None, description="股本结构")

    data_source: str = Field(..., description="数据来源")
    fetched_at: datetime = Field(default_factory=datetime.now, description="数据获取时间")
