import json
from redis.asyncio import Redis
from app.schemas.Event import EventIngest
from app.models.Tenant import Tenant

async def publish_events_batch(events: list[EventIngest], tenant: Tenant, redis: Redis):
    if not events:
        return

    pipe = redis.pipeline()
    stream_key = "events:stream"

    for event in events:
        await pipe.xadd(
            stream_key,
            {
                "tenant_id": str(tenant.id),
                "event_name": event.event_name,
                "payload": json.dumps(event.payload),
                "timestamp": event.timestamp.isoformat(),
                "retry_count": "0"
            },
            maxlen=10000,
            approximate=True
        )

    await pipe.execute()