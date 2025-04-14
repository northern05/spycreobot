import logging
from fastapi import APIRouter, status, Depends, Response
from fastapi.responses import FileResponse
from pathlib import Path

from . import dependencies, schemas

router = APIRouter(tags=["Portfolio"])

logger = logging.getLogger('portfolio/views')


@router.get(
    "/similar_assets",
    status_code=status.HTTP_200_OK,
    response_model=list[schemas.SimilarAssetsResponse] | schemas.SimilarAssetsResponse,
)
async def get_similar_assets(
        result: list[schemas.SimilarAssetsResponse] | schemas.SimilarAssetsResponse = Depends(
            dependencies.get_similar_assets)
):
    """
    Endpoint to get similar assets
    :return: similar_assets
    """
    return result


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[schemas.PortfolioResponse],
)
async def get_all_messages_count(
        result: list[schemas.PortfolioResponse] = Depends(dependencies.get_all_portfolio)
):
    """
    Endpoint to get portfolio over user
    :param session: session to connect to database
    :return: list portfolio
    """
    return result


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    response_model=schemas.PortfolioResponse,
)
async def create_portfolio(
        result: schemas.PortfolioResponse = Depends(dependencies.create_portfolio)
):
    """
    Endpoint to get portfolio over user
    :return: list portfolio
    """
    return result


@router.post(
    "/connect_telegram",
    status_code=status.HTTP_200_OK,
    # response_model=schemas.PortfolioResponse,
)
async def connect_tg(
        result: bool = Depends(dependencies.connect_tg)
):
    """
    Endpoint to get portfolio over user
    :return: list portfolio
    """
    return result


@router.get(
    "/selected",
    status_code=status.HTTP_200_OK,
    response_model=schemas.PortfolioResponseExtended,
)
async def get_selected_portfolio(
        result: schemas.PortfolioResponseExtended = Depends(dependencies.get_selected_portfolio)
):
    """
    Endpoint to get selected portfolio over user
    :return: portfolio extended schema
    """
    return result


@router.get(
    "/dataset",
    status_code=status.HTTP_200_OK,
)
async def get_dataset(
        result=Depends(dependencies.get_dataset)
):
    """
    Endpoint to get selected portfolio over user
    :return: portfolio extended schema
    """
    return result


@router.get(
    "/selected/chart",
    status_code=status.HTTP_200_OK,
    response_model=bytes,
)
async def get_selected_portfolio_chart(
        image_bytes: bytes = Depends(dependencies.get_selected_portfolio_chart)
):
    """
    Endpoint to get selected portfolio over user
    :return: portfolio extended schema
    """
    return Response(content=image_bytes, media_type="image/png")


@router.get(
    "/selected/sentiment",
    status_code=status.HTTP_200_OK,
    response_model=schemas.SentimentScore,
)
async def get_selected_portfolio_sentiment_score(
        result: schemas.SentimentScore = Depends(dependencies.get_sentiment_score)
):
    """
    Endpoint to get selected portfolio over user
    :return: portfolio extended schema
    """
    return result


@router.delete(
    "",
    status_code=status.HTTP_202_ACCEPTED
)
async def delete_portfolio(
        result: schemas.PortfolioResponseExtended = Depends(dependencies.delete_portfolio)
):
    """
    Endpoint to get selected portfolio over user
    :return: portfolio extended schema
    """
    return result


@router.get("/get-gif", response_class=FileResponse)
async def get_gif():
    gif_path = Path("gif_waiting.gif")
    return gif_path
