from fastapi import APIRouter

from .auth.views import router as auth_router
from .general.views import router as general_router

router = APIRouter()

router.include_router(router=auth_router, prefix="/auth")
router.include_router(router=general_router, prefix="/general")
