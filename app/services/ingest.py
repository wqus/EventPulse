import json
from redis.asyncio import Redis
from app.schemas.Event import EventIngest
from app.models.Tenant import Tenant

async def publish_event(
        event: EventIngest,
        tenant: Tenant,
        redis: Redis
):
    await redis.xadd(
        f"events:stream",
        {
            "tenant_id": str(tenant.id),
            "event_name": event.event_name,
            "payload": json.dumps(event.payload),
            "timestamp": event.timestamp.isoformat(),
            "retry_count": "0"
        }, maxlen=10000
    )