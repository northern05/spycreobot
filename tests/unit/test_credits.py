from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.credits import dependencies as dp
from app.api.credits.schemas import CreditsCheck
from app.core.models import Credits, User

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("amount,expected", [(-1, 0), (0, 0), (9.99, 0), (10, 5),
    (89.99, 5), (90, 50), (449.99, 50), (450, 250), (1000, 250)])
def test_credit_price_boundaries(amount, expected):
    assert dp.calculate_credits(amount) == expected


@pytest.mark.parametrize("balance", [0, -1, 1, 5])
async def test_spend_credit_or_reject_without_commit(monkeypatch, balance):
    session = MagicMock(spec=AsyncSession)
    credits = Credits(credits=balance)
    monkeypatch.setattr(dp.crud, "get_users_credits_by_telegram_id", AsyncMock(return_value=credits))
    if balance <= 0:
        with pytest.raises(HTTPException) as error:
            await dp.process_users_credits("123", session)
        assert error.value.status_code == 402
        assert credits.credits == balance
        session.commit.assert_not_awaited()
        session.close.assert_awaited_once()
    else:
        assert await dp.process_users_credits("123", session) is True
        assert credits.credits == balance - 1
        session.commit.assert_awaited_once()


async def test_system_user_bypasses_credit_lookup(monkeypatch):
    lookup = AsyncMock()
    monkeypatch.setattr(dp.crud, "get_users_credits_by_telegram_id", lookup)
    assert await dp.process_users_credits("0", MagicMock(spec=AsyncSession)) is True
    lookup.assert_not_awaited()


async def test_unknown_user_balance_returns_404(monkeypatch):
    session = MagicMock(spec=AsyncSession)
    monkeypatch.setattr(dp.crud, "get_users_credits_by_telegram_id", AsyncMock(return_value=None))
    monkeypatch.setattr(dp.auth_crud, "select_by_telegram_id", AsyncMock(return_value=None))
    with pytest.raises(HTTPException) as error:
        await dp.get_credits("123", session)
    assert error.value.status_code == 404
    session.close.assert_awaited_once()


async def test_missing_balance_is_initialized_at_zero(monkeypatch):
    session = MagicMock(spec=AsyncSession)
    monkeypatch.setattr(dp.crud, "get_users_credits_by_telegram_id", AsyncMock(return_value=None))
    monkeypatch.setattr(dp.auth_crud, "select_by_telegram_id", AsyncMock(return_value=User(id=3)))
    create = AsyncMock(return_value=Credits(credits=0, updated_at=datetime.now()))
    monkeypatch.setattr(dp.crud, "create", create)
    assert (await dp.get_credits("123", session)).credits == 0
    assert create.call_args.kwargs["credits_data"].user_id == 3


async def test_payment_for_another_user_is_rejected(monkeypatch, external_services):
    session = MagicMock(spec=AsyncSession)
    external_services.wallet_driver.get_transactions.return_value = [{"tx_hash": "tx", "from_address": "other"}]
    monkeypatch.setattr(dp.tr_crud, "get_by_tx_hash", AsyncMock(return_value=None))
    monkeypatch.setattr(dp.auth_dp, "check_telegram_id_wallet", AsyncMock(return_value=User(telegram_id="456")))
    create = AsyncMock()
    monkeypatch.setattr(dp.tr_crud, "create", create)
    with pytest.raises(HTTPException) as error:
        await dp.check_payment(CreditsCheck(telegram_id="123", credits=999), session)
    assert error.value.status_code == 404
    create.assert_not_awaited()


async def test_wallet_service_failure_propagates(external_services):
    external_services.wallet_driver.get_transactions.side_effect = RuntimeError("wallet offline")
    with pytest.raises(RuntimeError, match="wallet offline"):
        await dp.check_payment(CreditsCheck(telegram_id="123", credits=5), MagicMock(spec=AsyncSession))
