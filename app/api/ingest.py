import json
import logging

from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from app.schemas.Event import EventIngest
from app.models.Tenant import Tenant
from app.core.auth import get_tenant_by_api_key
from app.core.rate_limiting import check_rate_limit
from app.core.redis import get_redis
from logging import getLogger
router = APIRouter()

logger = getLogger(__name__)

logger.setLevel(logging.WARNING)

@router.post("/ingest")
async def ingest_event(
    event: EventIngest,
    tenant: Tenant = Depends(get_tenant_by_api_key),
    redis: Redis = Depends(get_redis)
):

    await check_rate_limit(str(tenant.id), tenant.plan, redis)

    await redis.xadd(
        "events:stream",
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

    return {"status": "ok"}
