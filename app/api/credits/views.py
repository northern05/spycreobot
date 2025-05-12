import logging
from fastapi import APIRouter, status, Depends, Response
from fastapi.responses import FileResponse
from pathlib import Path

from . import dependencies, schemas

router = APIRouter(tags=["Credits"])

logger = logging.getLogger('creatives/views')


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def check_payments(
        result: dict = Depends(dependencies.check_payment)
):
    """
        Endpoint check users payments
        :param session: session to connect to database
        :return: credits balance
        """
    return result

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=schemas.CreditsResponse,
)
async def get_credits(
        result: schemas.CreditsResponse = Depends(dependencies.get_credits)
):
    """
        Endpoint to get users credits
        :param session: session to connect to database
        :return: credits balance
        """
    return result
