from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import User


async def add_user(session: AsyncSession, wallet: str) -> User | None:
    """
    Method to create new user
    :param session: session to connect to database
    :param wallet: wallet address
    :return: user
    """
    user = User(wallet=wallet)
    session.add(user)
    await session.commit()
    return user


async def select_by_wallet(session: AsyncSession, wallet: str) -> User | None:
    """
    Method to select user by wallet
    :param session: session to connect to database
    :param wallet: wallet address
    :return: user
    """
    stmt = (
        select(User)
        .where(User.wallet == wallet)
    )

    result = await session.execute(stmt)
    user: User | None = result.scalars().first()
    return user

async def select_by_telegram_id(session: AsyncSession, telegram_id: str) -> User | None:
    """
    Method to select user by wallet
    :param session: session to connect to database
    :param telegram_id: users telegram id address
    :return: user
    """
    stmt = (
        select(User)
        .where(User.telegram_id == telegram_id)
    )

    result = await session.execute(stmt)
    user: User | None = result.scalars().first()
    return user
