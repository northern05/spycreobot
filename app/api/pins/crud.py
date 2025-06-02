from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import PinCreate
from app.core.models import Pin, User


async def create(session: AsyncSession, pin_data: PinCreate, user_id) -> Pin | None:
    pin = Pin(
        **pin_data.model_dump(),
        user_id=user_id
    )
    session.add(pin)
    await session.commit()
    return pin


async def get_users_pins(session: AsyncSession, telegram_id: str) -> list[Pin]:
    stmt = (
        select(Pin)
        .join(User, User.id == Pin.user_id)
        .filter(User.telegram_id == telegram_id)
    )
    result: Result = await session.execute(stmt)
    users_pins = result.scalars().all()
    return list(users_pins)
