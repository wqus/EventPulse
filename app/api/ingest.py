from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from app.schemas.Event import EventIngest,EventResponse
from app.models.Tenant import Tenant
from app.core.auth import get_tenant_by_api_key
from app.core.rate_limiting import check_rate_limit
from app.core.redis import get_redis
from app.services.ingest import publish_event

router = APIRouter()
@router.post("/ingest", response_model=EventResponse)
async def ingest_event(event: EventIngest, tenant: Tenant = Depends(get_tenant_by_api_key), redis: Redis = Depends(get_redis)):
    await check_rate_limit(str(tenant.id), tenant.plan.value, redis)
    await publish_event(event, tenant, redis)
    return EventResponse