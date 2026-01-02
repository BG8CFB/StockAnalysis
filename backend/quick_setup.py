#!/usr/bin/env python
"""
快速准备 MCP 测试数据
"""
import asyncio
import sys
from datetime import datetime, timezone
from bson import ObjectId

sys.path.insert(0, '.')

async def setup_test_data():
    from core.db.mongodb import mongodb

    await mongodb.connect()
    collection = mongodb.get_collection("mcp_servers")

    # 测试 MCP 服务器配置
    test_servers = [
        {
            "name": "memory",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "env": {},
            "url": None,
            "headers": {},
            "auth_type": "none",
            "auth_token": None,
            "auto_approve": [],
            "enabled": True,
            "is_system": True,
            "owner_id": None,
            "status": "unknown",
            "last_check_at": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        },
        {
            "name": "fetch",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-fetch"],
            "env": {},
            "url": None,
            "headers": {},
            "auth_type": "none",
            "auth_token": None,
            "auto_approve": [],
            "enabled": True,
            "is_system": True,
            "owner_id": None,
            "status": "unknown",
            "last_check_at": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        },
    ]

    for server_config in test_servers:
        existing = await collection.find_one({"name": server_config["name"]})
        if not existing:
            result = await collection.insert_one(server_config)
            print(f"[OK] Created MCP server: {server_config['name']} (ID: {result.inserted_id})")
        else:
            print(f"[SKIP] MCP server already exists: {server_config['name']}")

    await mongodb.disconnect()
    print("\nTest data setup complete!")

if __name__ == "__main__":
    asyncio.run(setup_test_data())
