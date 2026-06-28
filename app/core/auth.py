import hashlib
import logging
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, Header, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_session
from app.core.redis import get_redis
from app.models.Tenant import Tenant
from app.schemas.Tenant import TenantCache

logger = logging.getLogger(__name__)

CACHE_TTL_REDIS = 300
CACHE_TTL_MEMORY = 60
CACHE_PREFIX = "tenant:api:"

_memory_cache = {}


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def _create_tenant_from_cache(cache_data: TenantCache) -> Tenant:
    return Tenant(
        id=UUID(cache_data.id) if isinstance(cache_data.id, str) else cache_data.id,
        api_key_hash=cache_data.api_key_hash,
        is_active=cache_data.is_active,
        plan=cache_data.plan,
    )


async def _save_to_cache(tenant: Tenant, redis: Redis, cache_key: str, key_hash: str) -> None:
    try:
        cache_obj = TenantCache(
            id=str(tenant.id),
            api_key_hash=tenant.api_key_hash,
            is_active=tenant.is_active,
            plan=tenant.plan,
        )

        await redis.setex(
            cache_key,
            CACHE_TTL_REDIS,
            cache_obj.model_dump_json()
        )

        _memory_cache[key_hash] = (
            datetime.now().timestamp(),
            cache_obj
        )

        logger.debug(f"Tenant cached: {key_hash[:8]}")

    except Exception as e:
        logger.error(f" Failed to cache tenant: {e}")


async def get_tenant_by_api_key(x_api_key: str = Header(..., alias="X-API-Key"), redis: Redis = Depends(get_redis),
                                session: AsyncSession = Depends(get_session), ) -> Tenant:
    key_hash = hash_api_key(x_api_key)
    cache_key = f"{CACHE_PREFIX}{key_hash}"

    if key_hash in _memory_cache:
        cached_time, cached_data = _memory_cache[key_hash]
        if (datetime.now().timestamp() - cached_time) < CACHE_TTL_MEMORY:
            return _create_tenant_from_cache(cached_data)
        else:
            del _memory_cache[key_hash]

    try:
        cached = await redis.get(cache_key)
        if cached:
            if isinstance(cached, bytes):
                cached = cached.decode('utf-8')

            cache_obj = TenantCache.model_validate_json(cached)

            _memory_cache[key_hash] = (
                datetime.now().timestamp(),
                cache_obj)

            return _create_tenant_from_cache(cache_obj)

    except Exception as e:
        logger.warning(f"Redis cache error: {e}. Falling back to DB.")

    try:
        result = await session.execute(
            select(Tenant)
            .where(Tenant.api_key_hash == key_hash)
            .where(Tenant.is_active == True)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            logger.warning(f"Invalid API key: {key_hash[:8]}")
            raise HTTPException(
                status_code=401,
                detail="Invalid API key")

        await _save_to_cache(tenant, redis, cache_key, key_hash)

        return tenant

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DB error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error")


async def invalidate_tenant_cache(api_key: str, redis: Redis) -> None:
    key_hash = hash_api_key(api_key)
    cache_key = f"{CACHE_PREFIX}{key_hash}"

    await redis.delete(cache_key)

    if key_hash in _memory_cache:
        del _memory_cache[key_hash]
