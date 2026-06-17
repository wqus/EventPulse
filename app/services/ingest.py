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
        f"events:{tenant.id}",
        {
            "tenant_id": str(tenant.id),
            "event_name": event.event_name,
            "payload": json.dumps(event.payload),
            "timestamp": event.timestamp.isoformat()
        }, maxlen=10000
    )