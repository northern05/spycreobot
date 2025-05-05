from datetime import datetime, timedelta
from typing import Annotated
from fastapi import Path, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import errors
from app.core.models import db_helper
from app.api.transactions import crud as tr_crud
from app.api.transactions.schemas import *
from . import crud
from . import schemas
from app.api.auth import crud as auth_crud
from app.api.auth import dependencies as auth_dp
from app.core.modules_factory import wallet_driver
from app.core.config import CryptoSettings


async def get_credits(
        telegram_id: str,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    users_credits = await crud.get_users_credits_by_telegram_id(telegram_id=telegram_id, session=session)
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


async def check_payment(
        session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    account_transactions = wallet_driver.get_transactions(address=CryptoSettings.MASTER_WALLET)
    for tr in account_transactions:
        existing_tr = await tr_crud.get_by_tx_hash(session=session, tx_hash=tr.get("tx_hash"))
        if existing_tr: continue
        tr = await tr_crud.create(session=session, transaction_data=TransactionCreate.model_validate(tr))
        user = await auth_dp.check_telegram_id_wallet(session=session, wallet=tr.from_address)
        users_credits = await crud.get_users_credits_by_user_id(user_id=user.id, session=session)
        users_credits.credits += calculate_credits(amount=tr.amount)
        await session.commit()
    return True


def calculate_credits(amount: int):
    cred_count = 0
    if 90 > amount >= 10:
        cred_count = 5
    elif 450 > amount >= 90:
        cred_count = 50
    elif amount >= 450:
        cred_count = 250
    return cred_count
