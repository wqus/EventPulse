import asyncio

from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.database import AsyncSessionLocal
from app.core.redis import init_redis, close_redis, get_redis
from app.api.ingest import router as ingest_router
from app.api.metrics import router as metrics_router
from app.services.alert_checker import run_alert_checker
from app.api.alerts import router as alert_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    redis = await get_redis()
    checker_task = asyncio.create_task(
        run_alert_checker(AsyncSessionLocal, redis)
    )

    yield

    checker_task.cancel()
    await close_redis()


app = FastAPI(title='EventPulse', lifespan=lifespan)

app.include_router(ingest_router)
app.include_router(metrics_router)
app.include_router(alert_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
