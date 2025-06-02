from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import TransactionCreate
from app.core.models import Transaction


async def create(session: AsyncSession, transaction_data: TransactionCreate) -> Transaction | None:
    transaction = Transaction(
        **transaction_data.model_dump(),
    )
    session.add(transaction)
    await session.commit()
    return transaction


async def get_by_tx_hash(session: AsyncSession, tx_hash: str) -> Transaction | None:
    stmt = (
        select(Transaction).filter(Transaction.tx_hash == tx_hash)
    )
    result: Result = await session.execute(stmt)
    users_credits = result.scalars().first()
    return users_credits
