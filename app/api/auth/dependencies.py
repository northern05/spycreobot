from datetime import datetime
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import db_helper, User
from . import crud
from . import schemas
from app.api.credits import crud as credits_crud
from app.api.credits import schemas as credits_schemas


async def check_telegram_id_wallet(
        auth_in: schemas.AuthRequest,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> User:
    new_user = False
    if auth_in.telegram_id:
        user = await crud.select_by_telegram_id(session=session, telegram_id=auth_in.telegram_id)
    else:
        user = await crud.select_by_wallet(session=session, wallet=auth_in.wallet)
    if not user:
        user = await crud.add_user(session=session, telegram_id=auth_in.telegram_id, wallet=auth_in.wallet)
        new_user = True
    if not user.wallet or user.wallet != auth_in.wallet: user.wallet = auth_in.wallet
    if not user.telegram_id: user.telegram_id = auth_in.telegram_id
    if new_user: await credits_crud.create(
        session=session,
        credits_data=credits_schemas.CreditsCreate(user_id=user.id, credits=5, updated_at=datetime.now())
    )
    await session.commit()
    return user
