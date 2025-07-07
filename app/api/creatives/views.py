import logging
from fastapi import APIRouter, status, Depends
from fastapi.responses import FileResponse
from pathlib import Path
from . import dependencies

router = APIRouter(tags=["Creatives"])

logger = logging.getLogger('creatives/views')


@router.get(
    "/keyword",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def get_keyword_creatives(
        result: dict = Depends(dependencies.get_creatives)
):
    """
    Endpoint to get creatives over user
    :param result:
    :return: list creatives
    """
    return result


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def get_all(
        result: dict = Depends(dependencies.get_all)
):
    """
    Endpoint to get creatives over user
    :param result:
    :return: list creatives
    """
    return result


@router.get("/get-gif", response_class=FileResponse)
async def get_gif():
    gif_path = Path("gif_waiting.gif")
    return gif_path


@router.post(
    "/update_ads",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def get_all_creatives(
        result: dict = Depends(dependencies.update_all_creatives)
):
    """
    Endpoint to cash all ads
    """
    return result


@router.delete(
    "/{ad_id}",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def delete_pin(
        result: dict = Depends(dependencies.delete_ad)
):
    """
    Endpoint to delete users pins
    :param session: session to connect to database
    :return: dict with result
    """
    return result
