import logging
from fastapi import APIRouter, status, Depends

from . import dependencies

router = APIRouter(tags=["Pins"])

logger = logging.getLogger('pins/views')


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def save_pin(
        result: dict = Depends(dependencies.pin_creative_to_user)
):
    """
    Endpoint to save search params
    :param session: session to connect to database
    :return: list creatives
    """
    return result


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list,
)
async def save_pin(
        result: list = Depends(dependencies.get_users_pins)
):
    """
    Endpoint to all pins
    :param session: session to connect to database
    :return: list creatives
    """
    return result


@router.delete(
    "",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def delete_pin(
        result: list = Depends(dependencies.delete_pin)
):
    """
    Endpoint to delete users pins
    :param session: session to connect to database
    :return: list creatives
    """
    return result
