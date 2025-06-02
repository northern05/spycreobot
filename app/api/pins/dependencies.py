from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import PinCreate, Pin, PinResponse
from . import crud as pins_crud
from app.api.auth import crud as auth_crud
from app.core.models import db_helper


async def pin_creative_to_user(
        pin_data: PinCreate,
        telegram_id: str,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> dict:
    user = await auth_crud.select_by_telegram_id(
        telegram_id=telegram_id,
        session=session
    )
    result = await pins_crud.create(
        pin_data=pin_data,
        user_id=user.id,
        session=session
    )
    return {"ok": True}


async def get_users_pins(
        telegram_id: str,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> list[PinResponse]:
    result = await pins_crud.get_users_pins(
        session=session,
        telegram_id=telegram_id
    )
    return [PinResponse.from_orm(pin) for pin in result]
