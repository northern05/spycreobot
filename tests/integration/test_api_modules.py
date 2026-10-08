from datetime import datetime

import pytest
from sqlalchemy import select

from app.api.auth import crud as auth_crud
from app.api.credits import crud as credits_crud
from app.api.credits.schemas import CreditsCreate, CreditsUpdate
from app.api.creatives import crud as creatives_crud
from app.api.transactions import crud as transactions_crud
from app.api.transactions.schemas import TransactionCreate
from app.core.models import Credits, Creative, Pin, Transaction
from utils.paginated_response import paginate

pytestmark = pytest.mark.integration
PREFIX = "/bot/api/v1"
from tests.sample_data import PIN_DATA, creative_data

async def register(client, telegram_id="123", wallet="wallet-a"):
    response = await client.post(f"{PREFIX}/auth", json=dict(telegram_id=telegram_id, wallet=wallet))
    assert response.status_code == 200
    return response.json()["id"]




async def test_pin_create_list_isolation_and_delete(client, session_factory):
    await register(client)
    await register(client, "456", "wallet-b")
    for telegram_id in ("123", "456"):
        response = await client.post(f"{PREFIX}/pins", params={"telegram_id": telegram_id}, json=PIN_DATA)
        assert response.status_code == 200
        assert response.json() == {"ok": True}
    response = await client.get(f"{PREFIX}/pins", params={"telegram_id": "123"})
    assert response.status_code == 200
    pins = response.json()
    assert len(pins) == 1
    assert pins[0]["placements"] == PIN_DATA["placements"]
    assert pins[0]["keyword"] == "casino"
    response = await client.delete(f"{PREFIX}/pins/{pins[0]['id']}")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert (await client.get(f"{PREFIX}/pins", params={"telegram_id": "123"})).json() == []
    async with session_factory() as session:
        remaining = (await session.scalars(select(Pin))).all()
        assert len(remaining) == 1


@pytest.mark.parametrize("method,path,kwargs", [
    ("post", "/pins", {"params": {"telegram_id": "123"}, "json": {"niche": "gambling"}}),
    ("get", "/pins", {}),
    ("delete", "/pins/not-an-id", {}),
    ("get", "/credits", {}),
    ("post", "/credits", {"json": {"credits": 5}}),
    ("get", "/creatives", {"params": {"telegram_id": "123", "page_number": 0}}),
    ("get", "/creatives", {"params": {"telegram_id": "123", "page_size": 1002}}),
    ("delete", "/creatives/not-an-id", {}),
])
async def test_request_validation(client, method, path, kwargs):
    response = await client.request(method, PREFIX + path, **kwargs)
    assert response.status_code == 422


async def test_credit_balance_and_unknown_user(client):
    await register(client)
    response = await client.get(f"{PREFIX}/credits", params={"telegram_id": "123"})
    assert response.status_code == 200
    assert response.json()["credits"] == 5
    response = await client.get(f"{PREFIX}/credits", params={"telegram_id": "missing"})
    assert response.status_code == 404


async def test_credit_crud_round_trip_and_partial_update(session_factory):
    now = datetime.now()
    async with session_factory() as session:
        user = await auth_crud.add_user(session, "wallet", "123")
        credits = await credits_crud.create(session, CreditsCreate(user_id=user.id, credits=7, updated_at=now))
        await credits_crud.update_credits(session, credits, CreditsUpdate(credits=3), partial=True)
        credits_id = credits.id
        user_id = user.id
    async with session_factory() as session:
        by_user = await credits_crud.get_users_credits_by_user_id(session, user_id)
        by_telegram = await credits_crud.get_users_credits_by_telegram_id(session, "123")
        assert by_user.id == by_telegram.id == credits_id
        assert by_user.credits == 3
        assert by_user.updated_at == now
        assert await credits_crud.get_users_credits_by_user_id(session, 999) is None
        await credits_crud.delete_credits(session, by_user)
    async with session_factory() as session:
        assert await credits_crud.get_users_credits_by_user_id(session, user_id) is None


async def test_payment_adds_credits_once_using_asset_decimals(client, session_factory, external_services):
    user_id = await register(client)
    external_services.wallet_driver.get_transactions.return_value = [dict(
        tx_hash="tx-1", asset="USDT", amount=90_000_000, decimals=6,
        created_at=datetime.now().isoformat(), from_address="wallet-a")]
    payload = {"telegram_id": "123", "credits": 999999}
    first = await client.post(f"{PREFIX}/credits", json=payload)
    second = await client.post(f"{PREFIX}/credits", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json() == {"ok": True}
    assert second.json() == {"ok": False}
    async with session_factory() as session:
        credits = await credits_crud.get_users_credits_by_user_id(session, user_id)
        assert credits.credits == 55
        transactions = (await session.scalars(select(Transaction))).all()
        assert len(transactions) == 1
        assert transactions[0].tx_hash == "tx-1"


async def test_empty_payment_history_does_not_change_balance(client, session_factory):
    user_id = await register(client)
    response = await client.post(f"{PREFIX}/credits", json={"telegram_id": "123", "credits": 100})
    assert response.status_code == 200
    assert response.json() == {"ok": False}
    async with session_factory() as session:
        assert (await credits_crud.get_users_credits_by_user_id(session, user_id)).credits == 5


async def test_transaction_create_lookup_and_missing_hash(session_factory):
    async with session_factory() as session:
        await auth_crud.add_user(session, "wallet", "123")
        transaction = await transactions_crud.create(session, TransactionCreate(
            tx_hash="tx", asset="USDT", amount=10.5, created_at=datetime.now(), from_address="wallet"))
        transaction_id = transaction.id
    async with session_factory() as session:
        transaction = await transactions_crud.get_by_tx_hash(session, "tx")
        assert transaction.id == transaction_id
        assert transaction.amount == 10.5
        assert await transactions_crud.get_by_tx_hash(session, "missing") is None


async def test_creative_pagination_filter_and_credit_deduction(client, session_factory):
    user_id = await register(client)
    async with session_factory() as session:
        for number in range(3):
            await creatives_crud.create(session, creative_data(
                facebook_id=f"fb-{number}", media_unique_identifier=f"media-{number}", page_id="matching"))
        await creatives_crud.create(session, creative_data(
            facebook_id="other", media_unique_identifier="other", page_id="other"))
    response = await client.get(f"{PREFIX}/creatives", params=dict(
        telegram_id="123", objects_filter="page_id__eq=matching", page_size=2, page_number=1))
    assert response.status_code == 200
    data = response.json()
    assert data["total_items"] == 3
    assert data["total_pages"] == 2
    assert len(data["ads"]) == 2
    assert all(ad["page_id"] == "matching" and ad["days_running"] == 3 for ad in data["ads"])
    async with session_factory() as session:
        assert (await credits_crud.get_users_credits_by_user_id(session, user_id)).credits == 4


async def test_creative_soft_delete_and_duplicate_detection(client, session_factory, monkeypatch):
    async with session_factory() as session:
        creative = await creatives_crud.create(session, creative_data())
        creative_id = creative.id
    monkeypatch.setattr(creatives_crud.db_helper, "session_factory", session_factory)
    assert (await creatives_crud.check_creative("fb-1", "missing")).id == creative_id
    assert (await creatives_crud.check_creative("missing", "media-1")).id == creative_id
    assert await creatives_crud.check_creative("missing", "missing") is None
    response = await client.delete(f"{PREFIX}/creatives/{creative_id}")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    async with session_factory() as session:
        assert (await session.get(Creative, creative_id)).state == "deleted"


async def test_insufficient_balance_rejects_creative_search(client, session_factory):
    user_id = await register(client)
    async with session_factory() as session:
        await creatives_crud.create(session, creative_data())
        credits = await credits_crud.get_users_credits_by_user_id(session, user_id)
        credits.credits = 0
        await session.commit()
    response = await client.get(f"{PREFIX}/creatives", params={"telegram_id": "123"})
    assert response.status_code == 402
    async with session_factory() as session:
        assert (await credits_crud.get_users_credits_by_user_id(session, user_id)).credits == 0


async def test_live_creative_search_uses_real_credit_logic(client, session_factory, external_services):
    user_id = await register(client)
    external_services.fb_driver.get_ads_page.return_value = ([dict(
        id=1, title="Ad", platforms=["facebook"], facebook_url="https://example.com/ad",
        media_url="https://example.com/video", days_running=2, type="video", geo=["ua"])], {"cursor": "next"})
    response = await client.request("GET", f"{PREFIX}/creatives/keyword",
                                    json={"telegram_id": "123", "niche": "gambling"})
    assert response.status_code == 200
    assert len(response.json()["ads"]) == 1
    assert response.json()["after"] == {"cursor": "next"}
    async with session_factory() as session:
        assert (await credits_crud.get_users_credits_by_user_id(session, user_id)).credits == 4


async def test_pagination_second_page_and_orm_mode(session_factory):
    async with session_factory() as session:
        for number in range(3):
            await auth_crud.add_user(session, f"wallet-{number}", str(number))
        from app.core.models import User
        query = select(User).order_by(User.id)
        metadata, data = await paginate(session, query, page_number=2, page_size=2)
        assert metadata == dict(page_number=2, total_items=3, total_pages=2, page_size=2)
        assert [user.wallet for user in data] == ["wallet-2"]
        metadata, result = await paginate(session, query, page_number=1, page_size=2, orm=True)
        assert len(result.scalars().all()) == 2
        assert metadata["total_items"] == 3


async def test_general_policies_and_gif(client):
    response = await client.get(f"{PREFIX}/general/policies")
    assert response.status_code == 200
    assert response.json() == {"data": "This is my policies"}
    response = await client.get(f"{PREFIX}/creatives/get-gif")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/gif"
    assert response.content[:6] in (b"GIF87a", b"GIF89a")
