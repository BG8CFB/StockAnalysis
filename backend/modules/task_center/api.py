from fastapi import APIRouter

router = APIRouter(tags=["任务中心"])

@router.get("/tasks")
async def get_tasks():
    return {"tasks": []}
