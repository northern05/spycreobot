from fastapi import APIRouter

from .auth.views import router as auth_router
from .portfolio.views import router as statistics_router

router = APIRouter()

router.include_router(router=auth_router, prefix="/auth")
router.include_router(router=statistics_router, prefix="/portfolio")
