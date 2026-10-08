from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.credits import crud as credits
from app.api.credits.schemas import CreditsCreate
from app.api.creatives import crud as creatives
from app.api.pins import crud as pins, dependencies as pins_dp
from app.api.pins.schemas import PinCreate
from app.api.transactions import crud as transactions
from app.api.transactions.schemas import TransactionCreate
from app.core.models import User, Pin
from tests.sample_data import creative_data, PIN_DATA

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("module,data,extra,attribute,expected", [
    (credits, CreditsCreate(user_id=7, credits=5, updated_at=datetime.now()), {}, "credits", 5),
    (creatives, creative_data(), {}, "media_unique_identifier", "media-1"),
    (pins, PinCreate(**PIN_DATA), {"user_id": 7}, "user_id", 7),
    (transactions, TransactionCreate(tx_hash="tx", asset="USDT", amount=10,
        created_at=datetime.now(), from_address="wallet"), {}, "tx_hash", "tx"),
])
async def test_create_persists_model_and_propagates_commit_error(module, data, extra, attribute, expected):
    session = MagicMock(spec=AsyncSession)
    instance = await module.create(session, data, **extra)
    assert getattr(instance, attribute) == expected
    session.add.assert_called_once_with(instance)
    session.commit.assert_awaited_once()
    session.commit.side_effect = RuntimeError("database offline")
    with pytest.raises(RuntimeError, match="database offline"):
        await module.create(session, data, **extra)


async def test_pin_creation_uses_resolved_user_id(monkeypatch):
    session = MagicMock(spec=AsyncSession)
    lookup = AsyncMock(return_value=User(id=7))
    create = AsyncMock()
    monkeypatch.setattr(pins_dp.auth_crud, "select_by_telegram_id", lookup)
    monkeypatch.setattr(pins, "create", create)
    data = PinCreate(**PIN_DATA)
    assert await pins_dp.pin_creative_to_user(data, "123", session) == {"ok": True}
    lookup.assert_awaited_once_with(telegram_id="123", session=session)
    create.assert_awaited_once_with(pin_data=data, user_id=7, session=session)


async def test_pin_list_serializes_response_without_user_id(monkeypatch):
    monkeypatch.setattr(pins, "get_users_pins", AsyncMock(return_value=[Pin(id=2, user_id=7, **PIN_DATA)]))
    result = await pins_dp.get_users_pins("123", object())
    assert result[0].id == 2
    assert result[0].placements == ["facebook", "instagram"]
    assert "user_id" not in result[0].model_dump()


async def test_pin_deletion_delegates_to_crud(monkeypatch):
    delete = AsyncMock()
    monkeypatch.setattr(pins, "delete_pin", delete)
    session = object()
    assert await pins_dp.delete_pin(3, session) == {"ok": True}
    delete.assert_awaited_once_with(pin_id=3, session=session)
