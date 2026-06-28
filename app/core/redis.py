from redis.asyncio import Redis, ConnectionPool
from app.core.config import settings

redis_pool: ConnectionPool = None
redis_client: Redis = None


async def init_redis():
    global redis_pool, redis_client
    redis_pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=2000,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30,
    )
    redis_client = Redis(connection_pool=redis_pool)


async def get_redis() -> Redis:
    if redis_client is None:
        await init_redis()
    return redis_client


async def close_redis():
    global redis_client, redis_pool
    if redis_client:
        await redis_client.close()
    if redis_pool:
        await redis_pool.disconnect()