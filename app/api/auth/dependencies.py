from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import db_helper, User
from . import crud


async def check_telegram_id_wallet(
        telegram_id: str = None,
        wallet: str = None,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> User:
    if telegram_id:
        user = await crud.select_by_telegram_id(session=session, telegram_id=telegram_id)
    else:
        user = await crud.select_by_wallet(session=session, wallet=wallet)
    if not user:
        user = await crud.add_user(session=session, telegram_id=telegram_id, wallet=wallet)
    if not user.wallet: user.wallet = wallet
    if not user.telegram_id: user.telegram_id = telegram_id
    return user
