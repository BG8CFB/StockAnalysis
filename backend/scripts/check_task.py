import asyncio
import os
import sys
from bson import ObjectId
from datetime import datetime

# 添加 backend 目录到 sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from core.db.mongodb import mongodb

async def check_task(task_id_str):
    print(f"Connecting to database...")
    mongodb.connect()
    
    try:
        task_id = ObjectId(task_id_str)
        print(f"Checking task: {task_id}")
        
        task = await mongodb.database.analysis_tasks.find_one({"_id": task_id})
        
        if not task:
            print("❌ Task NOT FOUND")
            return
            
        print("\n=== Task Details ===")
        print(f"Status: {task.get('status')}")
        print(f"Progress: {task.get('progress')}")
        print(f"Phase: {task.get('current_phase')}")
        print(f"Agent: {task.get('current_agent')}")
        print(f"Created: {task.get('created_at')}")
        print(f"Started: {task.get('started_at')}")
        print(f"Completed: {task.get('completed_at')}")
        print(f"Error: {task.get('error_message')}")
        if task.get('error_details'):
            print(f"Error Details: {task.get('error_details')}")
            
        print(f"Reports: {list(task.get('reports', {}).keys())}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        mongodb.close()

if __name__ == "__main__":
    task_id = "696fa0f770e0aa75edee3fef"
    asyncio.run(check_task(task_id))
