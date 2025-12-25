from fastapi import APIRouter

router = APIRouter(prefix="/analysis/batch", tags=["批量分析"])

@router.get("/")
async def get_batch_analysis():
    return {"message": "Batch analysis module"}
