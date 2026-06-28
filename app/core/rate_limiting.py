import time
from fastapi import HTTPException
from redis.asyncio import Redis

RATE_LIMIT_LUA = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local now = tonumber(ARGV[2])
local window = tonumber(ARGV[3])

-- Удаляем старые записи
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

local count = redis.call('ZCARD', key)

if count >= limit then
    return {0, count}   -- rejected
end

redis.call('ZADD', key, now, now)
redis.call('EXPIRE', key, math.ceil(window) + 10)

return {1, count + 1}   -- allowed
"""

rate_limiter_script = None


async def check_rate_limit(tenant_id: str, plan: str, redis: Redis):
    key = f"rate_limit:{tenant_id}"

    limits = {
        "free": 100,
        "pro": 1000,
        "enterprise": 10000
    }
    limit = limits.get(plan, 100)
    now = time.time()
    window = 1.0

    result = await redis.eval(
        RATE_LIMIT_LUA,
        1,
        key,
        limit,
        now,
        window
    )

    allowed = result[0]
    count = result[1]

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": limit,
                "window": window,
                "current": count,
                "plan": plan
            }
        )

    return True