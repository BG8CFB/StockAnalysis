# -*- coding: utf-8 -*-
import asyncio
import aiohttp

BASE_URL = "http://localhost:8000/api"

async def main():
    async with aiohttp.ClientSession() as session:
        login_resp = await session.post(f"{BASE_URL}/users/login", json={"account": "test_ta_user", "password": "Test123456"})
        login_data = await login_resp.json()
        token = login_data.get("access_token", "")
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        request_data = {
            "stock_codes": ["000001.SZ"],
            "market": "a_share",
            "trade_date": "2024-01-15",
            "stages": {
                "stage1": {"enabled": True},
                "stage2": {"enabled": True},
                "stage3": {"enabled": True},
                "stage4": {"enabled": True}
            }
        }
        
        resp = await session.post(f"{BASE_URL}/trading-agents/tasks", json=request_data, headers=headers)
        print(f"Status: {resp.status}")
        text = await resp.text()
        print(f"Response: {text}")

if __name__ == "__main__":
    asyncio.run(main())
