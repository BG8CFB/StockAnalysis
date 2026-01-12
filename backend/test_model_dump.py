# -*- coding: utf-8 -*-
"""测试 Pydantic model_dump 行为"""
import sys
sys.path.insert(0, '.')

from modules.trading_agents.schemas import (
    UserAgentConfigResponse,
    Phase1Config,
    AgentConfig,
    MCPServerConfig
)

# 模拟数据库返回的文档结构
db_doc = {
    "_id": "test_id",
    "user_id": "system_public",
    "is_public": True,
    "is_customized": False,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "phase1": {
        "enabled": True,
        "max_rounds": 1,
        "max_concurrency": 3,
        "agents": [
            {
                "slug": "market_technical",
                "name": "技术分析师",
                "role_definition": "你是技术分析师",
                "when_to_use": "分析技术面",
                "enabled_mcp_servers": [],
                "enabled_local_tools": [],
                "enabled": True
            }
        ]
    }
}

print("=" * 60)
print("测试 1: 直接创建 Phase1Config 对象")
print("=" * 60)

phase1_data = db_doc["phase1"]
phase1_obj = Phase1Config(**phase1_data)

print(f"phase1_obj type: {type(phase1_obj)}")
print(f"phase1_obj.agents type: {type(phase1_obj.agents)}")
print(f"phase1_obj.agents[0] type: {type(phase1_obj.agents[0])}")
print(f"Has model_dump: {hasattr(phase1_obj, 'model_dump')}")

print("\n调用 model_dump(mode='json'):")
dumped = phase1_obj.model_dump(mode='json')
print(f"dumped type: {type(dumped)}")
print(f"dumped['agents'] type: {type(dumped['agents'])}")
print(f"dumped['agents'][0] type: {type(dumped['agents'][0])}")
print(f"dumped['agents'][0].get('slug'): {dumped['agents'][0].get('slug')}")

print("\n" + "=" * 60)
print("测试 2: UserAgentConfigResponse.from_db()")
print("=" * 60)

config = UserAgentConfigResponse.from_db(db_doc)
print(f"config type: {type(config)}")
print(f"config.phase1 type: {type(config.phase1)}")
print(f"config.phase1.agents type: {type(config.phase1.agents)}")
print(f"config.phase1.agents[0] type: {type(config.phase1.agents[0])}")

print("\n调用 config.model_dump(mode='json'):")
config_dumped = config.model_dump(mode='json')
print(f"config_dumped type: {type(config_dumped)}")
print(f"config_dumped['phase1'] type: {type(config_dumped['phase1'])}")
print(f"config_dumped['phase1']['agents'] type: {type(config_dumped['phase1']['agents'])}")
print(f"config_dumped['phase1']['agents'][0] type: {type(config_dumped['phase1']['agents'][0])}")

# 测试 .get() 方法
try:
    slug = config_dumped['phase1']['agents'][0].get('slug')
    print(f"✅ .get('slug') 成功: {slug}")
except AttributeError as e:
    print(f"❌ .get() 失败: {e}")

# 直接访问
try:
    slug = config_dumped['phase1']['agents'][0]['slug']
    print(f"✅ 直接访问成功: {slug}")
except (KeyError, TypeError) as e:
    print(f"❌ 直接访问失败: {e}")

print("\n" + "=" * 60)
print("测试 3: 检查 agent 对象本身")
print("=" * 60)

agent = config.phase1.agents[0]
print(f"agent type: {type(agent)}")
print(f"agent.slug: {agent.slug}")
print(f"agent.get('slug') - 尝试调用:")
try:
    result = agent.get('slug')
    print(f"  成功: {result}")
except AttributeError as e:
    print(f"  失败: {e}")

print("\n" + "=" * 60)
print("结论:")
print("=" * 60)
print("model_dump(mode='json') 后，agents[0] 是 dict 类型")
print("但 Pydantic AgentConfig 对象没有 .get() 方法")
print("解决方案：在需要字典的地方确保已调用 model_dump()")
