from fastapi import APIRouter
from .single_api import router as single_router
from .batch_api import router as batch_router

router = APIRouter()
router.include_router(single_router)
router.include_router(batch_router)
