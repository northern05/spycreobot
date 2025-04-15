from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import db_helper, User
from . import crud


async def check_telegram_id(
        telegram_id: str,
        wallet: str,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> User:
    user = await crud.select_by_telegram_id(session=session, telegram_id=telegram_id)
    if not user:
        user = await crud.add_user(session=session, telegram_id=telegram_id, wallet=wallet)
    return user
