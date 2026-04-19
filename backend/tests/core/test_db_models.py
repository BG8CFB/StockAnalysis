"""
测试数据库模型
"""

import pytest
from bson import ObjectId

from core.db.models import PyObjectId


class TestPyObjectId:
    """PyObjectId 类型测试"""

    def test_validate_from_string(self) -> None:
        """从字符串创建 PyObjectId"""
        oid_str = str(ObjectId())
        result = PyObjectId.validate(oid_str)
        assert isinstance(result, ObjectId)

    def test_validate_from_objectid(self) -> None:
        """从 ObjectId 实例创建"""
        oid = ObjectId()
        result = PyObjectId.validate(oid)
        assert result == oid

    def test_validate_invalid_string(self) -> None:
        """无效字符串应抛出异常"""
        with pytest.raises(ValueError, match="Invalid ObjectId"):
            PyObjectId.validate("not_a_valid_id")

    def test_validate_empty_string(self) -> None:
        """空字符串应抛出异常"""
        with pytest.raises(ValueError):
            PyObjectId.validate("")

    def test_pydantic_schema(self) -> None:
        """Pydantic core schema 生成正常"""
        schema = PyObjectId.__get_pydantic_core_schema__(PyObjectId, None)  # type: ignore[arg-type]
        assert schema is not None
