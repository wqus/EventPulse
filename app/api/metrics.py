from fastapi import APIRouter, Query
from fastapi.params import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_tenant_by_api_key
from app.core.database import get_session
from app.core.redis import get_redis
from app.models.Tenant import Tenant
from app.schemas.metrics import MetricsResponse, TimeseriesResponse
from app.services.metrics import get_metrics_cached, get_timeseries_cached

router = APIRouter()

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics_endpoint(period: str = Query(default="1h",pattern="^(1h|24h|7d)$"),
                               tenant: Tenant = Depends(get_tenant_by_api_key),
                               session: AsyncSession = Depends(get_session),
                               redis: Redis = Depends(get_redis)):
    return await get_metrics_cached(tenant.id, period, session, redis)

@router.get("/metrics/timeseries", response_model=TimeseriesResponse)
async def get_timeseries_endpoint(period: str = Query(default="1h", pattern="^(1h|24h|7d)$"),
                                  tenant: Tenant = Depends(get_tenant_by_api_key),
                                  session: AsyncSession = Depends(get_session),
                                  redis: Redis = Depends(get_redis)):
    return await get_timeseries_cached(tenant.id, period, session, redis)


