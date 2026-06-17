from fastapi import HTTPException
from redis.asyncio import Redis
import time

PLAN_LIMITS = {
    "free": 10,
    "pro": 100,
    "enterprise": 1000
}

async def check_rate_limit(tenant_id: str, plan: str, redis: Redis):
    key = f"rate_limit:{tenant_id}"
    limit = PLAN_LIMITS.get(plan, 10)
    now = time.time()
    window = 1.0

    await redis.zremrangebyscore(key, 0, now - window)

    count = await redis.zcard(key)

    if count >= limit:
        raise HTTPException(
            status_code=409, detail=f"Rate limit exceeded. Plan {plan}, limit: {limit} RPS"
        )

    await redis.zadd(key, {str(now): now})
    await redis.expire(key,2)