from sqlalchemy import select, func
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import PortfolioCreate, PortfolioUpdate, PortfolioResponse
from app.core.models import Portfolio, PortfolioUser, User


async def get_users_assets(session: AsyncSession, telegram_id: str) -> list | None:
    stmt = (
        select(Portfolio)
        .join(PortfolioUser, PortfolioUser.portfolio_id == Portfolio.id)
        .filter(PortfolioUser.telegram_id == telegram_id)
        .order_by(Portfolio.symbol)
    )
    result: Result = await session.execute(stmt)
    users_portfolio = result.scalars().all()
    return [PortfolioResponse.from_orm(portfolio) for portfolio in users_portfolio]


async def create(session: AsyncSession, portfolio_data: PortfolioCreate) -> Portfolio | None:
    portfolio = await get_by_symbol(session=session, symbol=portfolio_data.symbol)
    if not portfolio:
        portfolio = Portfolio(
            **portfolio_data.model_dump(exclude={"telegram_id"}),
        )
        session.add(portfolio)
        await session.commit()
    portfolio_user_stmt = (
        select(PortfolioUser)
        .filter(PortfolioUser.telegram_id == portfolio_data.telegram_id)
        .filter(PortfolioUser.portfolio_id == portfolio.id)
    )
    result: Result = await session.execute(portfolio_user_stmt)
    portfolio_user = result.scalars().first()
    if not portfolio_user:
        portfolio_user = PortfolioUser(portfolio_id=portfolio.id, telegram_id=portfolio_data.telegram_id)
        session.add(portfolio_user)
        await session.commit()
    return portfolio


async def get_by_id(session: AsyncSession, portfolio_id: int) -> Portfolio | None:
    stmt = (
        select(Portfolio)
        .filter(Portfolio.id == portfolio_id)
    )
    result: Result = await session.execute(stmt)
    portfolio = result.scalars().first()
    return portfolio


async def get_by_symbol(session: AsyncSession, symbol: str) -> Portfolio | None:
    stmt = (
        select(Portfolio)
        .filter(func.lower(Portfolio.symbol) == symbol.lower())
    )
    result: Result = await session.execute(stmt)
    portfolio = result.scalars().first()
    return portfolio


async def get_all(session: AsyncSession):
    result: Result = await session.execute(select(Portfolio))
    portfolios = result.scalars().all()
    return portfolios


async def update_portfolio(
        session: AsyncSession,
        portfolio: Portfolio,
        portfolio_update: PortfolioUpdate,
        partial: bool = False,
) -> Portfolio:
    for name, value in portfolio_update.model_dump(exclude_unset=partial).items():
        setattr(portfolio, name, value)
    await session.commit()
    return portfolio


async def delete_project(
        session: AsyncSession,
        portfolio: Portfolio,
) -> None:
    await session.delete(portfolio)
    await session.commit()


async def delete_users_portfolio(
        session: AsyncSession,
        symbol: str,
        telegram_id: str
):
    stmt = (
        select(PortfolioUser)
        .join(Portfolio, Portfolio.id == PortfolioUser.portfolio_id)
        .filter(PortfolioUser.telegram_id == telegram_id)
        .filter(func.lower(Portfolio.symbol) == symbol.lower())
    )
    result: Result = await session.execute(stmt)
    portfolio = result.scalars().first()
    await session.delete(portfolio)
    await session.commit()
    return True


async def get_similar_assets(
        session: AsyncSession,
        symbol: str
):
    stmt = (
        select(Portfolio.coingecko_id)
        .filter(func.lower(Portfolio.symbol).ilike(f'%{symbol.lower()}%'))
    )
    result: Result = await session.execute(stmt)
    portfolios = result.scalars().all()
    return portfolios
