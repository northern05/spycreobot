from sqlalchemy import select, func
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import CreditsCreate, CreditsUpdate, CreditsBase, ConnectTelegram
from app.core.models import Credits, User


async def get_users_credits_by_telegram_id(session: AsyncSession, telegram_id: str) -> Credits | None:
    stmt = (
        select(Credits)
        .join(User, User.id == Credits.user_id)
        .filter(User.telegram_id == telegram_id)
    )
    result: Result = await session.execute(stmt)
    users_credits = result.scalars().first()
    return users_credits


async def get_users_credits_by_user_id(session: AsyncSession, user_id: int) -> Credits | None:
    stmt = (
        select(Credits)
        .filter(Credits.user_id == user_id)
    )
    result: Result = await session.execute(stmt)
    users_credits = result.scalars().first()
    return users_credits


async def create(session: AsyncSession, credits_data: CreditsCreate) -> Credits | None:
    credits_in = Credits(
        **credits_data.model_dump(exclude={"telegram_id"}),
    )
    session.add(credits_in)
    await session.commit()
    return credits_in


async def update_credits(
        session: AsyncSession,
        credits_in: Credits,
        credits_update: CreditsUpdate,
        partial: bool = False,
) -> Credits:
    for name, value in credits_update.model_dump(exclude_unset=partial).items():
        setattr(credits_in, name, value)
    await session.commit()
    return credits_in


async def delete_credits(
        session: AsyncSession,
        credits_in: Credits,
) -> None:
    await session.delete(credits_in)
    await session.commit()
