"""
TradingAgents schemas 模型测试
"""

from datetime import datetime

import pytest

from modules.trading_agents.schemas import (
    AnalysisTaskCreate,
    UnifiedTaskCreate,
    parse_datetime,
)


class TestAnalysisTaskCreate:
    """任务创建模型测试"""

    def test_valid_create_request(self) -> None:
        req = AnalysisTaskCreate(
            stock_code="600519",
            trade_date="2024-01-15",
            data_collection_model="Qwen3.6-35B-A3B",
            debate_model="Qwen3.6-35B-A3B",
        )  # type: ignore[call-arg]
        assert req.stock_code == "600519"
        assert req.trade_date == "2024-01-15"
        assert req.data_collection_model == "Qwen3.6-35B-A3B"

    def test_stock_code_validation(self) -> None:
        with pytest.raises(Exception):
            AnalysisTaskCreate(stock_code="", trade_date="2024-01-15")  # type: ignore[call-arg]

    def test_with_model_config(self) -> None:
        req = AnalysisTaskCreate(
            stock_code="600519",
            trade_date="2024-01-15",
            data_collection_model="Qwen3.6-35B-A3B",
            debate_model="Qwen3.6-35B-A3B",
        )  # type: ignore[call-arg]
        assert req.data_collection_model == "Qwen3.6-35B-A3B"
        assert req.debate_model == "Qwen3.6-35B-A3B"


class TestUnifiedTaskCreate:
    """统一任务创建模型测试"""

    def test_valid_unified_create(self) -> None:
        req = UnifiedTaskCreate(
            stock_codes=["600519"],
            trade_date="2024-01-15",
        )  # type: ignore[call-arg]
        assert req.stock_codes == ["600519"]


class TestParseDatetime:
    """日期解析测试"""

    def test_parse_none(self) -> None:
        assert parse_datetime(None) is None

    def test_parse_datetime_object(self) -> None:
        dt = datetime(2024, 1, 15, 10, 30)
        assert parse_datetime(dt) == dt

    def test_parse_iso_string(self) -> None:
        result = parse_datetime("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024

    def test_parse_mongo_extended_json(self) -> None:
        result = parse_datetime({"$date": "2024-01-15T10:30:00.000Z"})
        assert result is not None
        assert result.year == 2024

    def test_parse_invalid_string(self) -> None:
        result = parse_datetime("not-a-date")
        assert result is None

    def test_parse_invalid_type(self) -> None:
        result = parse_datetime(12345)
        assert result is None
