from fastapi import APIRouter

router = APIRouter(prefix="/analysis/single", tags=["单个分析"])

@router.get("/")
async def get_single_analysis():
    return {"message": "Single analysis module"}
