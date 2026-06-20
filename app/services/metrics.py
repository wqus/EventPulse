import json
import uuid
from datetime import datetime

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.metrics import get_metrics, get_timeseries

CACHE_TTL = {
    "1h": 60,
    "24h": 300,
    "7d": 3600
}


def _serialize(data: dict) -> str:
    d = dict(data)
    d["from_time"] = d["from_time"].isoformat()
    d["to_time"] = d["to_time"].isoformat()
    return json.dumps(d)


def _deserialize(raw: str) -> dict:
    d = json.loads(raw)
    d["from_time"] = datetime.fromisoformat(d["from_time"])
    d["to_time"] = datetime.fromisoformat(d["to_time"])
    return d


async def get_metrics_cached(tenant_id: uuid.UUID, period: str, session: AsyncSession, redis: Redis) -> dict:
    cache_key = f"metrics:{tenant_id}:{period}"
    cached = await redis.get(cache_key)

    if cached:
        return _deserialize(cached)

    data = await get_metrics(tenant_id, period, session)

    ttl = CACHE_TTL.get(period, 60)
    await redis.set(cache_key, _serialize(data), ex=ttl)

    return data


async def get_timeseries_cached(
        tenant_id: uuid.UUID,
        period: str,
        session: AsyncSession,
        redis: Redis
) -> dict:
    cache_key = f"timeseries:{tenant_id}:{period}"

    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    data = await get_timeseries(tenant_id, period, session)

    serializable = dict(data)
    serializable["points"] = [
        {**p, "bucket": p["bucket"].isoformat()} for p in data["points"]
    ]

    ttl = CACHE_TTL.get(period, 60)
    await redis.set(cache_key, json.dumps(serializable), ex = ttl)

    return data