from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import db_helper
from app.api.transactions import crud as tr_crud
from app.api.transactions.schemas import *
from . import crud
from . import schemas
from app.api.auth import crud as auth_crud
from app.api.auth import dependencies as auth_dp
from app.api.auth.schemas import AuthRequest
from app.core.modules_factory import wallet_driver
from app.core.config import crypto_config
from app.core.errors import errors


async def process_users_credits(
        telegram_id: str,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    if int(telegram_id) == 0: return True
    users_credits = await crud.get_users_credits_by_telegram_id(telegram_id=telegram_id, session=session)
    if users_credits.credits <= 0:
        await session.close()
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=errors.credit_errors.INSUFFICIENT_BALANCE
        )
    users_credits.credits -= 1
    await session.commit()
    return True


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
            credits_data=schemas.CreditsCreate(user_id=user.id, credits=0, updated_at=datetime.now())
        )
    return schemas.CreditsResponse.from_orm(users_credits)


async def check_payment(
        check_data: schemas.CreditsCheck,
        session: AsyncSession = Depends(db_helper.scoped_session_dependency)
):
    result = []
    account_transactions = await wallet_driver.get_transactions(address=crypto_config.MASTER_WALLET)
    for tr in account_transactions:
        existing_tr = await tr_crud.get_by_tx_hash(session=session, tx_hash=tr.get("tx_hash"))
        if existing_tr: continue
        user = await auth_dp.check_telegram_id_wallet(session=session, auth_in=AuthRequest(wallet=tr.get("from_address")))
        if user.telegram_id != check_data.telegram_id:
            await session.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=errors.credit_errors.USER_NOT_EXISTS
            )

        transaction = await tr_crud.create(session=session, transaction_data=TransactionCreate.model_validate(tr))
        result.append(transaction.id)
        users_credits = await crud.get_users_credits_by_user_id(user_id=user.id, session=session)
        users_credits.credits += calculate_credits(amount=tr.get("amount") / 10**tr.get("decimals"))
        await session.commit()
    return {"ok": True if result else False}


def calculate_credits(amount: int):
    cred_count = 0
    if 90 > amount >= 10:
        cred_count = 5
    elif 450 > amount >= 90:
        cred_count = 50
    elif amount >= 450:
        cred_count = 250
    return cred_count
