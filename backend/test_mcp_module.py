"""测试 MCP 模块功能"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api"

async def test_health_check():
    """测试 MCP 健康检查"""
    print("\n=== 测试 MCP 健康检查 ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/mcp/health")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"健康状态: {data}")


async def test_list_servers():
    """测试获取服务器列表"""
    print("\n=== 测试获取服务器列表 ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/mcp/servers")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"系统服务器数量: {data.get('system_count', 0)}")
            print(f"用户服务器数量: {data.get('user_count', 0)}")
        else:
            print(f"响应: {response.text}")


async def test_create_server():
    """测试创建 MCP 服务器"""
    print("\n=== 测试创建 MCP 服务器 ===")
    async with httpx.AsyncClient() as client:
        # 测试数据 - 创建一个简单的测试服务器
        test_server = {
            "name": "测试文件系统 MCP",
            "transport": "stdio",
            "command": "python",
            "args": ["-m", "mcp.server.cli"],
            "env": {},
            "enabled": False,
            "is_system": False
        }
        response = await client.post(f"{BASE_URL}/mcp/servers", json=test_server)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"服务器 ID: {data.get('id')}")
            print(f"服务器名称: {data.get('name')}")
            return data.get('id')
        else:
            print(f"响应: {response.text}")
            return None


async def test_get_server(server_id):
    """测试获取单个服务器"""
    print(f"\n=== 测试获取服务器 {server_id} ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/mcp/servers/{server_id}")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"服务器: {data.get('name')}")
            print(f"状态: {data.get('status')}")
            print(f"传输模式: {data.get('transport')}")
        else:
            print(f"响应: {response.text}")


async def test_pool_stats():
    """测试连接池统计（需要管理员权限）"""
    print("\n=== 测试连接池统计 ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/mcp/pool/stats")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"活跃连接数: {data.get('active_connections', 0)}")
            print(f"总连接数: {data.get('total_connections', 0)}")
        else:
            print(f"响应: {response.text}")


async def main():
    """运行所有测试"""
    print("=" * 50)
    print("开始 MCP 模块功能测试")
    print("=" * 50)
    
    try:
        await test_health_check()
        await test_list_servers()
        server_id = await test_create_server()
        if server_id:
            await test_get_server(server_id)
        await test_pool_stats()
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
