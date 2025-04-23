import logging
from fastapi import APIRouter, status, Depends, Response
from fastapi.responses import FileResponse
from pathlib import Path


router = APIRouter(tags=["Portfolio"])

logger = logging.getLogger('portfolio/views')


@router.get(
    "/policies",
)
async def get_similar_assets(
):
    """
    Endpoint to get similar assets
    :return: similar_assets
    """
    return {"data": "This is my policies"}
