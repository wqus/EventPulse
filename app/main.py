from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.redis import init_redis, close_redis
from app.api.ingest import router as ingest_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    yield
    await close_redis()


app = FastAPI(title='EventPulse', lifespan=lifespan)

app.include_router(ingest_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}