import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.Tenant import Tenant


async def find_by_api_key_hash(key_hash: str, session: AsyncSession) -> Tenant | None:
    result = await session.execute(
        select(Tenant)
        .where(Tenant.api_key_hash == key_hash)
        .where(Tenant.is_active == True)
    )
    return result.scalar_one_or_none()


async def set_telegram_chat_id(tenant: Tenant, chat_id: str, session: AsyncSession) -> None:
    tenant.telegram_chat_id = chat_id
    await session.commit()


async def get_by_id(tenant_id: uuid.UUID, session: AsyncSession) -> Tenant | None:
    result = await session.execute(
        select(Tenant).where(Tenant.id == tenant_id))
    return result.scalar_one_or_none()