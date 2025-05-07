import logging
from fastapi import APIRouter, Depends

from app.core.models import User
from . import dependencies

logger = logging.getLogger("auth/views")

router = APIRouter(
    tags=["Authorization"],
    responses={404: {"description": "Not found"}},
)


@router.post("")
async def me(
        user: User = Depends(dependencies.check_telegram_id_wallet),
):
    """
    Endpoint to return user's wallet connected
    :param user: user extracted from access token
    :return: user's wallet
    """
    return user
