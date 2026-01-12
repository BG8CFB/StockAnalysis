# -*- coding: utf-8 -*-
"""
完整的工作流测试脚本 - 使用 requests 库
模拟前端操作流程：检查系统状态、初始化（需要）、登录、配置模型、创建任务
"""

import requests
import json
import time
from datetime import datetime

# API 基础 URL
BASE_URL = "http://localhost:8000/api"

# 管理员账号（初始化时创建）
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_EMAIL = "admin@example.com"

# AI 模型配置
AI_MODEL_CONFIG = {
    "name": "GLM-4.7",
    "platform_type": "custom",
    "platform_name": "zhipu",
    "api_base_url": "https://api.z.ai/api/coding/paas/v4",
    "api_key": "0c2ef49f7a7149fab64be7a725c6f759.9a72qZtM3vlTlic2",
    "model_id": "glm-4.7",
    "max_concurrency": 40,
    "task_concurrency": 2,
    "batch_concurrency": 1,
    "timeout_seconds": 60,
    "temperature": 0.5,
    "enabled": True,
    "thinking_enabled": False,
    "thinking_mode": None,
    "is_system": True
}

# MCP 服务器配置
MCP_SERVER_CONFIG = {
    "name": "Sequential Thinking",
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
    "env": {},
    "enabled": True
}


def log_step(step_num, title):
    """打印步骤标题"""
    print("\n" + "=" * 70)
    print(f"Step {step_num}: {title}")
    print("=" * 70)


def check_system_status():
    """1. 检查系统状态"""
    log_step(1, "检查系统状态")
    
    url = f"{BASE_URL}/system/status"
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return data.get("initialized", False)
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def initialize_system():
    """2. 初始化系统（如果需要）"""
    log_step(2, "初始化系统")
    
    url = f"{BASE_URL}/system/initialize"
    payload = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
        "email": ADMIN_EMAIL
    }
    
    try:
        print(f"Request Payload: {json.dumps(payload, indent=2)}")
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print("系统初始化成功！")
            return True
        else:
            print(f"系统初始化失败: {response.json()}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def login():
    """3. 登录管理员账号"""
    log_step(3, "登录管理员账号")
    
    url = f"{BASE_URL}/users/login"
    payload = {
        "account": ADMIN_USERNAME,  # 使用 account 字段
        "password": ADMIN_PASSWORD
    }
    
    try:
        print(f"Login Payload: {json.dumps(payload, indent=2)}")
        # 增加超时时间到 60 秒
        response = requests.post(url, json=payload, timeout=60)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            token = data.get("access_token")
            print(f"登录成功! Token: {token[:50]}...")
            return token
        else:
            print(f"登录失败: {response.json()}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_ai_model(token):
    """4. 创建 AI 模型配置"""
    log_step(4, "创建 AI 模型配置")
    
    url = f"{BASE_URL}/ai/models"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        print(f"Request Payload: {json.dumps(AI_MODEL_CONFIG, indent=2)}")
        response = requests.post(url, json=AI_MODEL_CONFIG, headers=headers, timeout=60)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            data = response.json()
            model_id = data.get("id")
            print(f"AI 模型创建成功！ID: {model_id}")
            return model_id
        else:
            print(f"AI 模型创建失败: {response.json()}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def list_ai_models(token):
    """列出 AI 模型"""
    log_step(5, "列出 AI 模型")
    
    url = f"{BASE_URL}/ai/models"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            # 如果有系统模型，使用第一个
            system_models = data.get("system", [])
            if system_models:
                model_id = system_models[0].get("id")
                print(f"使用现有系统模型，ID: {model_id}")
                return model_id
            return None
        else:
            print(f"获取模型列表失败: {response.json()}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def create_mcp_server(token):
    """6. 创建 MCP 服务器配置"""
    log_step(6, "创建 MCP 服务器配置")
    
    url = f"{BASE_URL}/mcp/servers"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        print(f"Request Payload: {json.dumps(MCP_SERVER_CONFIG, indent=2)}")
        response = requests.post(url, json=MCP_SERVER_CONFIG, headers=headers, timeout=60)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            data = response.json()
            server_id = data.get("id")
            print(f"MCP 服务器创建成功！ID: {server_id}")
            return server_id
        else:
            print(f"MCP 服务器创建失败: {response.json()}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def list_mcp_servers(token):
    """列出 MCP 服务器"""
    log_step(7, "列出 MCP 服务器")
    
    url = f"{BASE_URL}/mcp/servers"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            # 如果有服务器，使用第一个
            all_servers = data.get("system", []) + data.get("user", [])
            if all_servers:
                server_id = all_servers[0].get("id")
                print(f"使用现有 MCP 服务器，ID: {server_id}")
                return server_id
            return None
        else:
            print(f"获取 MCP 服务器列表失败: {response.json()}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def create_analysis_task(token, model_id, mcp_server_id=None):
    """8. 创建分析任务"""
    log_step(8, "创建分析任务")
    
    # 计算今天的日期
    today = datetime.now().strftime("%Y-%m-%d")
    
    url = f"{BASE_URL}/trading-agents/tasks"
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "stock_codes": ["000001"],  # 平安银行
        "market": "a_share",
        "trade_date": today,
        "data_collection_model": model_id,
        "debate_model": model_id,
        "stages": {
            "stage1": {
                "enabled": True,
                "selected_agents": ["technical_analyst", "fundamental_analyst"]
            },
            "stage2": {
                "enabled": True,
                "debate": {"rounds": 3}
            },
            "stage3": {
                "enabled": True
            },
            "stage4": {
                "enabled": True
            }
        }
    }
    
    try:
        print(f"Request Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id") or data.get("batch_id")
            print(f"分析任务创建成功！ID: {task_id}")
            return task_id
        else:
            print(f"分析任务创建失败: {response.json()}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_task_status(token, task_id):
    """9. 获取任务状态"""
    log_step(9, "获取任务状态")
    
    url = f"{BASE_URL}/trading-agents/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print("获取任务状态成功！")
            return True
        else:
            print(f"获取任务状态失败: {response.json()}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """主测试流程"""
    print("\n" + "=" * 70)
    print("开始测试完整工作流".center(70))
    print("=" * 70)
    
    token = None
    model_id = None
    mcp_server_id = None
    task_id = None
    
    try:
        # 1. 检查系统状态
        initialized = check_system_status()
        
        # 2. 如果未初始化，则初始化系统
        if not initialized:
            success = initialize_system()
            if not success:
                print("\n系统初始化失败，终止测试")
                return
        else:
            print("\n等待 5 秒，让系统初始化完成...")
            time.sleep(5)
        
        # 3. 登录
        token = login()
        if not token:
            print("\n登录失败，终止测试")
            return
        
        # 4. 尝试创建 AI 模型
        model_id = create_ai_model(token)
        
        # 如果创建失败，可能已存在，列出可用模型
        if not model_id:
            model_id = list_ai_models(token)
        
        # 5. 测试 AI 模型连接（如果有模型）
        if model_id:
            print(f"\n  注意：可以测试模型连接，但需要额外配置")
        
        # 6. 尝试创建 MCP 服务器
        mcp_server_id = create_mcp_server(token)
        
        # 如果创建失败，可能已存在，列出可用服务器
        if not mcp_server_id:
            mcp_server_id = list_mcp_servers(token)
        
        # 7. 创建分析任务（如果有模型）
        if model_id:
            task_id = create_analysis_task(token, model_id, mcp_server_id)
            
            # 8. 获取任务状态（如果有任务）
            if task_id:
                get_task_status(token, task_id)
        else:
            print("\n没有可用的 AI 模型，无法创建分析任务")
        
        # 总结
        print("\n" + "=" * 70)
        print("测试完成".center(70))
        print("=" * 70)
        print(f"\n总结:")
        print(f"  - Token: {token[:50]}..." if token else "  - Token: None")
        print(f"  - AI 模型 ID: {model_id}")
        print(f"  - MCP 服务器 ID: {mcp_server_id}")
        print(f"  - 任务 ID: {task_id}")
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
