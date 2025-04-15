from datetime import datetime, timedelta
from typing import Annotated
from fastapi import Path, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import dependencies as auth_dependencies
from app.core.errors import errors
from app.core.models import db_helper
from . import crud
from . import schemas
from app.api.auth import crud as auth_crud


async def get_credits(
        telegram_id: str,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    users_credits = await crud.get_users_credits(telegram_id=telegram_id, session=session)
    if not users_credits:
        user = await auth_crud.select_by_telegram_id(telegram_id=telegram_id, session=session)
        if not user:
            await session.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=errors.credit_errors.USER_NOT_EXISTS
            )
        users_credits = await crud.create(
            session=session,
            credits_data=schemas.CreditsCreate(credits=0, updated_at=datetime.now())
        )
    return schemas.CreditsResponse.from_orm(users_credits)
