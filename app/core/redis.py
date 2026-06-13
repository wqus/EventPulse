from redis.asyncio import Redis
from app.core.config import settings

redis_client: Redis = None

async def get_redis() -> Redis:
    return redis_client

async def init_redis():
    global redis_client
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses = True)

async def close_redis():
    await redis_client.close()