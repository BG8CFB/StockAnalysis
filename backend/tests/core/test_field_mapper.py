"""
测试字段映射工具
"""

from core.market_data.tools.field_mapper import FieldMapper


class TestFieldMapper:
    """字段映射器基类测试"""

    def test_normalize_symbol_with_exchange(self) -> None:
        result = FieldMapper.normalize_symbol("600519", "SH")
        assert result == "600519.SH"

    def test_normalize_symbol_infer_sse(self) -> None:
        """6 开头的 A 股推断为上交所 SSE"""
        result = FieldMapper.normalize_symbol("600519")
        assert result == "600519.SSE"

    def test_normalize_symbol_infer_szse(self) -> None:
        """0 开头的 A 股推断为深交所 SZSE"""
        result = FieldMapper.normalize_symbol("000001")
        assert result == "000001.SZSE"

    def test_normalize_symbol_infer_szse_3(self) -> None:
        """3 开头的创业板推断为深交所 SZSE"""
        result = FieldMapper.normalize_symbol("300001")
        assert result == "300001.SZSE"

    def test_normalize_symbol_already_normalized(self) -> None:
        """已经包含交易所后缀的代码不变"""
        result = FieldMapper.normalize_symbol("600519.SH")
        assert result == "600519.SH"

    def test_normalize_date_yyyymmdd(self) -> None:
        """标准日期格式"""
        result = FieldMapper.normalize_date("20240101")
        assert result == "20240101"

    def test_normalize_date_iso(self) -> None:
        """ISO 日期格式转换"""
        result = FieldMapper.normalize_date("2024-01-01")
        assert result == "20240101"

    def test_normalize_date_empty(self) -> None:
        result = FieldMapper.normalize_date("")
        assert result == ""

    def test_normalize_date_none(self) -> None:
        result = FieldMapper.normalize_date(None)  # type: ignore[arg-type]
        assert result == ""

    def test_safe_float_valid(self) -> None:
        result = FieldMapper.safe_float(123.45)
        assert result == 123.45

    def test_safe_float_string(self) -> None:
        result = FieldMapper.safe_float("123.45")
        assert result == 123.45

    def test_safe_float_invalid(self) -> None:
        result = FieldMapper.safe_float("abc")
        assert result is None

    def test_safe_float_none(self) -> None:
        result = FieldMapper.safe_float(None)
        assert result is None

    def test_safe_float_empty_string(self) -> None:
        result = FieldMapper.safe_float("")
        assert result is None

    def test_safe_int_valid(self) -> None:
        result = FieldMapper.safe_int(42)
        assert result == 42

    def test_safe_int_string(self) -> None:
        result = FieldMapper.safe_int("42")
        assert result == 42

    def test_safe_int_invalid(self) -> None:
        result = FieldMapper.safe_int("abc")
        assert result is None

    def test_safe_int_none(self) -> None:
        result = FieldMapper.safe_int(None)
        assert result is None

    def test_convert_amount_yuan_to_wanyuan(self) -> None:
        result = FieldMapper.convert_amount(10000, "yuan", "wanyuan")
        assert result == 1.0

    def test_convert_amount_same_unit(self) -> None:
        result = FieldMapper.convert_amount(1000, "yuan", "yuan")
        assert result == 1000

    def test_convert_amount_none(self) -> None:
        result = FieldMapper.convert_amount(None, "yuan", "wanyuan")
        assert result is None
