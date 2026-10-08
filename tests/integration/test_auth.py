import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.auth import crud
from app.core.models import Credits, User

pytestmark = pytest.mark.integration
AUTH_URL = "/bot/api/v1/auth"


@pytest.mark.parametrize("telegram_id", ["123", None])
async def test_registration_and_repeat_auth_do_not_duplicate_users_or_credits(
    client, session_factory, telegram_id
):
    payload = {"wallet": "wallet-a", "telegram_id": telegram_id}
    first = await client.post(AUTH_URL, json=payload)
    second = await client.post(AUTH_URL, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["wallet"] == "wallet-a"
    assert first.json()["created_at"]
    if telegram_id:
        assert first.json()["telegram_id"] == telegram_id

    async with session_factory() as session:
        users = (await session.scalars(select(User))).all()
        credits = (await session.scalars(select(Credits))).all()
        assert len(users) == len(credits) == 1
        assert credits[0].user_id == users[0].id == first.json()["id"]
        assert credits[0].credits == 5


async def test_wallet_change_is_persisted_without_resetting_balance(client, session_factory):
    response = await client.post(AUTH_URL, json={"wallet": "old", "telegram_id": "123"})
    assert response.status_code == 200
    user_id = response.json()["id"]
    async with session_factory() as session:
        credits = await session.scalar(select(Credits).where(Credits.user_id == user_id))
        credits.credits = 2
        await session.commit()

    response = await client.post(AUTH_URL, json={"wallet": "new", "telegram_id": "123"})
    assert response.status_code == 200
    assert response.json()["id"] == user_id
    async with session_factory() as session:
        user = await crud.select_by_telegram_id(session, "123")
        assert user.wallet == "new"
        assert await crud.select_by_wallet(session, "old") is None
        credits = (await session.scalars(select(Credits))).all()
        assert len(credits) == 1
        assert credits[0].credits == 2


async def test_crud_round_trip_and_missing_user(session_factory):
    async with session_factory() as session:
        assert await crud.select_by_wallet(session, "missing") is None
        assert await crud.select_by_telegram_id(session, "missing") is None
        user = await crud.add_user(session, "wallet-a", "123")
        user_id = user.id
    async with session_factory() as session:
        by_wallet = await crud.select_by_wallet(session, "wallet-a")
        by_telegram = await crud.select_by_telegram_id(session, "123")
        assert by_wallet.id == by_telegram.id == user_id


async def test_duplicate_wallet_is_rejected_by_database(session_factory):
    async with session_factory() as session:
        await crud.add_user(session, "wallet-a", "123")
        with pytest.raises(IntegrityError):
            await crud.add_user(session, "wallet-a", "456")
        await session.rollback()
    async with session_factory() as session:
        users = (await session.scalars(select(User))).all()
        assert len(users) == 1
        assert users[0].telegram_id == "123"


@pytest.mark.parametrize("payload", [{"wallet": []}, {"telegram_id": {}}, None])
async def test_invalid_request_returns_422_without_creating_users(client, session_factory, payload):
    response = await client.post(AUTH_URL, json=payload)
    assert response.status_code == 422
    async with session_factory() as session:
        assert (await session.scalars(select(User))).all() == []
        assert (await session.scalars(select(Credits))).all() == []
