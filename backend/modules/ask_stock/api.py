from fastapi import APIRouter

router = APIRouter(tags=["AI 问股"])

@router.post("/ask")
async def ask_stock(question: str):
    return {"answer": f"AI analysis for: {question}"}
