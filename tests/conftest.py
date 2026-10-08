"""Load API modules without running the external-service bootstrap."""

import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest_asyncio
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import JSON, event


ROOT = Path(__file__).resolve().parents[1]
# These package initializers eagerly import the entire app and external drivers.
# Keep normal submodule loading, but skip only those bootstrap initializers.
for name, directory in (("app", ROOT / "app"), ("app.api", ROOT / "app/api")):
    package = ModuleType(name)
    package.__path__ = [str(directory)]
    sys.modules[name] = package

# Settings are instantiated at import time. Use test-only values, never secrets.
for key in (
    "DB_NAME", "DB_USER", "DB_HOST", "DB_PW", "REDIS_HOST", "REDIS_USER",
    "REDIS_PASSWORD", "MASTER_WALLET", "TRON_API_URL", "USDT_CONTRACT",
    "ACCESS_TOKEN", "APP_ID", "APP_SECRET",
):
    os.environ[key] = "test"
os.environ["DB_PORT"] = "5432"
os.environ["REDIS_PORT"] = "6379"
os.environ["SQLALCHEMY_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.api.auth.views import router  # noqa: E402
from app.core.models import Base, Credits, User, db_helper  # noqa: E402

# Substitute external service boundaries, keeping the application logic real.
services = ModuleType("app.core.modules_factory")
services.wallet_driver = SimpleNamespace(get_transactions=AsyncMock(return_value=[]))
services.fb_driver = SimpleNamespace(get_ads_page=AsyncMock(return_value=([], None)))
services.redis_db = SimpleNamespace()
sys.modules[services.__name__] = services

from app.api.credits.views import router as credits_router
from app.api.creatives.views import router as creatives_router
from app.api.pins.views import router as pins_router
from app.api.general.views import router as general_router
from app.core.models import Creative, Pin

# SQLite cannot store PostgreSQL ARRAYs. JSON preserves list round trips in
# portable integration tests; PostgreSQL array predicates are tested separately.
for column in (Creative.platforms, Creative.geo, Pin.placements):
    mapped_column = column.property.columns[0]
    mapped_column.type = mapped_column.type.with_variant(JSON(), "sqlite")


@pytest.fixture(autouse=True)
def reset_external_services():
    services.wallet_driver.get_transactions.reset_mock(return_value=True, side_effect=True)
    services.wallet_driver.get_transactions.return_value = []
    services.fb_driver.get_ads_page.reset_mock(return_value=True, side_effect=True)
    services.fb_driver.get_ads_page.return_value = ([], None)


@pytest.fixture
def external_services():
    return services


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'auth.db'}")
    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection
            )
        )
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def client(session_factory):
    application = FastAPI()
    application.include_router(router, prefix="/bot/api/v1/auth")
    for name, api_router in (("credits", credits_router), ("creatives", creatives_router),
                             ("pins", pins_router), ("general", general_router)):
        application.include_router(api_router, prefix=f"/bot/api/v1/{name}")

    async def test_session():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    application.dependency_overrides[db_helper.scoped_session_dependency] = test_session
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as http_client:
        yield http_client
