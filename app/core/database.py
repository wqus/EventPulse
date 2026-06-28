import logging
from logging import getLogger
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    pool_size = 20,
    max_overflow = 20,
    echo = False
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_ = AsyncSession,
    expire_on_commit = False
)

logger = getLogger(__name__)

logger.setLevel(logging.WARNING)

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session