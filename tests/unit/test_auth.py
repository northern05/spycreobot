
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import crud, dependencies
from app.api.auth.schemas import AuthRequest
from app.core.models import User

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("field", ["wallet", "telegram_id"])
@pytest.mark.parametrize("found", [True, False])
async def test_lookup_filters_by_requested_identity(field, found):
    session = MagicMock(spec=AsyncSession)
    user = User(id=7, wallet="wallet-a", telegram_id="123") if found else None
    result = MagicMock()
    result.scalars.return_value.first.return_value = user
    session.execute.return_value = result

    lookup = getattr(crud, f"select_by_{field}")
    assert await lookup(session=session, **{field: "requested-id"}) is user
    statement = session.execute.call_args.args[0]
    assert f"users.{field} =" in str(statement)
    assert "requested-id" in statement.compile().params.values()


async def test_add_user_persists_supplied_identity():
    session = MagicMock(spec=AsyncSession)
    user = await crud.add_user(session, "wallet-a", "123")
    assert (user.wallet, user.telegram_id) == ("wallet-a", "123")
    session.add.assert_called_once_with(user)
    session.commit.assert_awaited_once()


async def test_add_user_propagates_database_failure():
    session = MagicMock(spec=AsyncSession)
    session.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    with pytest.raises(IntegrityError):
        await crud.add_user(session, "wallet-a", "123")


@pytest.mark.parametrize("telegram_id", ["123", None])
@pytest.mark.parametrize("existing", [True, False])
async def test_auth_lookup_and_initial_credits(monkeypatch, telegram_id, existing):
    session = MagicMock(spec=AsyncSession)
    user = User(id=7, wallet="wallet-a", telegram_id=telegram_id)
    telegram_lookup = AsyncMock(return_value=user if existing else None)
    wallet_lookup = AsyncMock(return_value=user if existing else None)
    add_user = AsyncMock(return_value=user)
    create_credits = AsyncMock()
    monkeypatch.setattr(crud, "select_by_telegram_id", telegram_lookup)
    monkeypatch.setattr(crud, "select_by_wallet", wallet_lookup)
    monkeypatch.setattr(crud, "add_user", add_user)
    monkeypatch.setattr(dependencies.credits_crud, "create", create_credits)

    assert await dependencies.check_telegram_id_wallet(
        AuthRequest(wallet="wallet-a", telegram_id=telegram_id), session
    ) is user
    if telegram_id:
        telegram_lookup.assert_awaited_once_with(session=session, telegram_id=telegram_id)
        wallet_lookup.assert_not_awaited()
    else:
        wallet_lookup.assert_awaited_once_with(session=session, wallet="wallet-a")
        telegram_lookup.assert_not_awaited()
    if existing:
        add_user.assert_not_awaited()
        create_credits.assert_not_awaited()
    else:
        add_user.assert_awaited_once_with(
            session=session, telegram_id=telegram_id, wallet="wallet-a"
        )
        create_credits.assert_awaited_once()
        credits = create_credits.call_args.kwargs["credits_data"]
        assert (credits.user_id, credits.credits) == (7, 5)
        assert credits.updated_at is not None
    session.commit.assert_awaited_once()


async def test_existing_telegram_user_can_update_wallet(monkeypatch):
    session = MagicMock(spec=AsyncSession)
    user = User(id=7, wallet="old-wallet", telegram_id="123")
    monkeypatch.setattr(crud, "select_by_telegram_id", AsyncMock(return_value=user))
    create_credits = AsyncMock()
    monkeypatch.setattr(dependencies.credits_crud, "create", create_credits)
    await dependencies.check_telegram_id_wallet(
        AuthRequest(wallet="new-wallet", telegram_id="123"), session
    )
    assert user.wallet == "new-wallet"
    create_credits.assert_not_awaited()
    session.commit.assert_awaited_once()
