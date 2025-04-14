from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import db_helper, User
from . import crud
from app.core import errors


async def check_wallet(
        wallet_address: str,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> User:
    """
    Method to return user by wallet address
    :param wallet_address: wallet address to check
    :param session: session to connect to database
    :return: user
    """
    user = await crud.select_by_wallet(session=session, wallet=wallet_address)
    if not user:
        user = await crud.add_user(session=session, wallet=wallet_address)
    return user


async def check_telegram_id(
        telegram_id: str,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> User:
    user = await crud.select_by_telegram_id(session=session, telegram_id=telegram_id)
    if not user:
        await session.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=errors.PortfolioErrors.TELEGRAM_NOT_CONNECTED
        )
    return user
