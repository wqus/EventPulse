import hashlib
from fastapi import HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_session
from app.models.Tenant import Tenant

def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()

async def get_tenant_by_api_key(
        x_api_key: str = Header(...),
        session: AsyncSession = Depends(get_session)
) -> Tenant:
    key_hash = hash_api_key(x_api_key)

    result = await session.execute(
        select(Tenant)
        .where(Tenant.api_key_hash == key_hash)
        .where(Tenant.is_active == True)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return tenant