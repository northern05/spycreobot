from sqlalchemy import select, func
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import TransactionCreate
from app.core.models import Transaction, User


async def create(session: AsyncSession, transaction_data: TransactionCreate) -> Transaction | None:
    transaction = Transaction(
        **transaction_data.model_dump(),
    )
    session.add(transaction)
    await session.commit()
    return transaction
