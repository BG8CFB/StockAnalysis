from fastapi import APIRouter

router = APIRouter(tags=["智能选股"])

@router.get("/screener/strategies")
async def get_strategies():
    return {"strategies": []}
