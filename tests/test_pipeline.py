import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from app.models.Tenant import Tenant
from app.models.Event import Event
from app.consumer import process_batch, STREAM_KEY, DEAD_LETTER_KEY, ensure_group, GROUP_NAME
from tests.conftest import session_factory

VALID_EVENT = {
    "event_name": "payment.failed",
    "payload": {"user_id": 123, "error": "insufficient_funds"},
    "timestamp": "2026-06-08T10:00:00Z",
}


@pytest.mark.asyncio
async def test_single_event(client, test_tenant: Tenant, redis_client, db_session, session_factory):
    response = await client.post(
        "/ingest",
        json=VALID_EVENT,
        headers={"X-API-Key": "test_api_key_123"},
    )
    assert response.status_code == 200

    await ensure_group(redis_client)

    result = await redis_client.xreadgroup(
        groupname=GROUP_NAME,
        consumername="test-consumer",
        streams={STREAM_KEY: ">"},
        count=10,
        block=1000,
    )
    assert result, "Сообщение не дошло до Stream"

    _, messages = result[0]
    await process_batch(redis_client, messages, session_factory=session_factory)

    rows = await db_session.execute(select(Event).where(Event.tenant_id == test_tenant.id))
    events = rows.scalars().all()

    assert len(events) == 1
    assert events[0].event_name == "payment.failed"
    assert events[0].payload["user_id"] == 123


@pytest.mark.asyncio
async def test_broken_event(redis_client, db_session, session_factory):
    await ensure_group(redis_client)

    await redis_client.xadd(
        STREAM_KEY,
        {
            "tenant_id": "00000000-0000-0000-0000-000000000000",
            "event_name": "broken.event",
            "payload": "!!!",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    result = await redis_client.xreadgroup(
        groupname=GROUP_NAME,
        consumername="test-consumer",
        streams={STREAM_KEY: ">"},
        count=10,
        block=1000,
    )
    _, messages = result[0]

    await process_batch(redis_client, messages, session_factory=session_factory)

    dlq_length = await redis_client.xlen(DEAD_LETTER_KEY)
    assert dlq_length >= 1

    pending = await redis_client.xpending(STREAM_KEY, GROUP_NAME)
    assert pending["pending"] == 0


@pytest.mark.asyncio
async def test_multiple_events(client, test_tenant: Tenant, redis_client, db_session, session_factory):
    for i in range(5):
        event = dict(VALID_EVENT)
        event["payload"] = {"user_id": i}
        await client.post(
            "/ingest",
            json=event,
            headers={"X-API-Key": "test_api_key_123"},
        )

    await ensure_group(redis_client)
    result = await redis_client.xreadgroup(
        groupname=GROUP_NAME,
        consumername="test-consumer",
        streams={STREAM_KEY: ">"},
        count=10,
        block=1000,
    )
    _, messages = result[0]
    await process_batch(redis_client, messages, session_factory = session_factory)

    rows = await db_session.execute(select(Event).where(Event.tenant_id == test_tenant.id))
    events = rows.scalars().all()
    assert len(events) == 5