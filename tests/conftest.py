from uuid import uuid4

import pytest_asyncio
from redis.asyncio import Redis
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.auth import hash_api_key
from app.core.database import get_session
from app.core.redis import get_redis
from app.models.Tenant import Tenant, Plan
from app.models.base import Base
from app.main import app

from app.core.config import settings

ASYNC_DATABASE_URL_TEST = settings.ASYNC_DATABASE_URL_TEST


@pytest_asyncio.fixture(scope="function")
async def engine():
    engine = create_async_engine(
        ASYNC_DATABASE_URL_TEST
    )

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.drop_all
        )

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session_factory(engine):
    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    return session_maker


@pytest_asyncio.fixture(scope="function")
async def db_session(session_factory):
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise



@pytest_asyncio.fixture(scope="function")
async def redis_client():
    redis = Redis.from_url(
        settings.REDIS_TEST_URL,
        decode_responses=True
    )

    await redis.delete("events:stream", "events:dead_letter")

    keys = await redis.keys("rate_limit:test-*")

    if keys:
        await redis.delete(*keys)

    yield redis

    await redis.delete("events:stream", "events:dead_letter")

    await redis.aclose()


@pytest_asyncio.fixture(scope="function")
async def test_tenant(db_session: AsyncSession) -> Tenant:
    tenant = Tenant(id=uuid4(), name="Test Tenant", plan=Plan.PRO,
                    api_key_hash=hash_api_key("test_api_key_123"))

    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture(scope="function")
async def client(
        db_session: AsyncSession,
        redis_client: Redis):
    async def override_get_session():
        yield db_session

    async def override_get_redis():
        yield redis_client

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
