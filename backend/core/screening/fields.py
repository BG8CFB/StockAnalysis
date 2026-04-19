"""
筛选字段定义

定义所有可用于筛选的字段，包括类型、范围、单位等信息。
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScreeningFieldDef:
    """筛选字段定义"""
    name: str
    display_name: str
    type: str  # number, string, enum
    unit: str = ""
    description: str = ""
    min: float | None = None
    max: float | None = None
    enum_values: list[str] = field(default_factory=list)
    db_field: str = ""  # MongoDB 中对应的字段路径
    category: str = "basic"  # basic, financial, technical

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "label": self.display_name,
            "description": self.description,
        }
        if self.unit:
            result["unit"] = self.unit
        if self.min is not None:
            result["min"] = self.min
        if self.max is not None:
            result["max"] = self.max
        if self.enum_values:
            result["enum_values"] = self.enum_values
        return result


# ==================== 字段定义列表 ====================

SCREENING_FIELDS: list[ScreeningFieldDef] = [
    # --- 基本面指标 ---
    ScreeningFieldDef(
        name="pe_ttm",
        display_name="市盈率(TTM)",
        type="number",
        unit="倍",
        min=0,
        max=1000,
        db_field="pe_ttm",
        category="financial",
        description="滚动市盈率",
    ),
    ScreeningFieldDef(
        name="pe",
        display_name="市盈率(静态)",
        type="number",
        unit="倍",
        min=0,
        max=1000,
        db_field="pe",
        category="financial",
        description="静态市盈率",
    ),
    ScreeningFieldDef(
        name="pb",
        display_name="市净率",
        type="number",
        unit="倍",
        min=0,
        max=100,
        db_field="pb_mrq",
        category="financial",
        description="市净率(MRQ)",
    ),
    ScreeningFieldDef(
        name="ps_ttm",
        display_name="市销率(TTM)",
        type="number",
        unit="倍",
        min=0,
        max=200,
        db_field="ps_ttm",
        category="financial",
        description="滚动市销率",
    ),
    ScreeningFieldDef(
        name="total_mv",
        display_name="总市值",
        type="number",
        unit="亿元",
        min=0,
        max=1000000,
        db_field="total_mv",
        category="basic",
        description="总市值(亿元)",
    ),
    ScreeningFieldDef(
        name="circ_mv",
        display_name="流通市值",
        type="number",
        unit="亿元",
        min=0,
        max=1000000,
        db_field="circ_mv",
        category="basic",
        description="流通市值(亿元)",
    ),
    ScreeningFieldDef(
        name="roe",
        display_name="净资产收益率",
        type="number",
        unit="%",
        min=-100,
        max=100,
        db_field="roe",
        category="financial",
        description="ROE",
    ),
    ScreeningFieldDef(
        name="roa",
        display_name="总资产收益率",
        type="number",
        unit="%",
        min=-100,
        max=100,
        db_field="roa",
        category="financial",
        description="ROA",
    ),
    ScreeningFieldDef(
        name="net_profit_margin",
        display_name="净利率",
        type="number",
        unit="%",
        min=-100,
        max=100,
        db_field="net_profit_margin",
        category="financial",
        description="净利率",
    ),
    ScreeningFieldDef(
        name="gross_profit_margin",
        display_name="毛利率",
        type="number",
        unit="%",
        min=-100,
        max=100,
        db_field="gross_profit_margin",
        category="financial",
        description="毛利率",
    ),
    ScreeningFieldDef(
        name="debt_ratio",
        display_name="资产负债率",
        type="number",
        unit="%",
        min=0,
        max=100,
        db_field="debt_to_assets",
        category="financial",
        description="资产负债率",
    ),
    ScreeningFieldDef(
        name="revenue",
        display_name="营业收入",
        type="number",
        unit="亿元",
        min=0,
        db_field="income_statement.total_revenue",
        category="financial",
        description="最近一期营业收入(亿元)",
    ),
    ScreeningFieldDef(
        name="net_income",
        display_name="净利润",
        type="number",
        unit="亿元",
        db_field="income_statement.net_profit",
        category="financial",
        description="最近一期净利润(亿元)",
    ),
    # --- 技术面指标 ---
    ScreeningFieldDef(
        name="pct_chg",
        display_name="涨跌幅",
        type="number",
        unit="%",
        min=-30,
        max=30,
        db_field="pct_chg",
        category="technical",
        description="最新涨跌幅",
    ),
    ScreeningFieldDef(
        name="volume",
        display_name="成交量",
        type="number",
        unit="手",
        min=0,
        db_field="volume",
        category="technical",
        description="最新成交量",
    ),
    ScreeningFieldDef(
        name="turnover_rate",
        display_name="换手率",
        type="number",
        unit="%",
        min=0,
        max=100,
        db_field="turnover_rate",
        category="technical",
        description="换手率",
    ),
    ScreeningFieldDef(
        name="volume_ratio",
        display_name="量比",
        type="number",
        unit="倍",
        min=0,
        max=100,
        db_field="volume_ratio",
        category="technical",
        description="量比",
    ),
    ScreeningFieldDef(
        name="amplitude",
        display_name="振幅",
        type="number",
        unit="%",
        min=0,
        max=30,
        db_field="amplitude",
        category="technical",
        description="振幅",
    ),
    # --- 基本属性 ---
    ScreeningFieldDef(
        name="market",
        display_name="市场",
        type="enum",
        enum_values=["A_STOCK", "US_STOCK", "HK_STOCK"],
        db_field="market",
        category="basic",
        description="所属市场",
    ),
    ScreeningFieldDef(
        name="industry",
        display_name="行业",
        type="string",
        db_field="industry",
        category="basic",
        description="所属行业",
    ),
]

# 字段名到定义的映射
FIELDS_MAP: dict[str, ScreeningFieldDef] = {f.name: f for f in SCREENING_FIELDS}

# 按类别分组
FIELD_CATEGORIES: dict[str, list[str]] = {}
for f in SCREENING_FIELDS:
    FIELD_CATEGORIES.setdefault(f.category, []).append(f.name)
