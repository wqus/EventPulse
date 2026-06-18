import asyncio
import json
import logging
from datetime import datetime
import uuid

from redis.asyncio import Redis

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.Event import Event

logger = logging.getLogger("consumer")

STREAM_KEY = "events:stream"
DEAD_LETTER_KEY = "events:dead_letter"
GROUP_NAME = "events:consumers"
CONSUMER_NAME = f"consumer-{uuid.uuid4()}"

BATCH_SIZE = 100
BLOCK_MS = 1000

MAX_RETRIES = 3


async def ensure_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
        logger.info("Consumer group created")
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            raise
        logger.info("Consumer group already exists")


def parse_message(message_id: str, data: dict) -> Event | None:
    try:
        return Event(
            tenant_id=data["tenant_id"],
            event_name=data["event_name"],
            payload=json.loads(data["payload"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )
    except (KeyError, json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse message {message_id}: {e}")
        return None


async def send_to_dead_letter(redis: Redis, message_id: str, data: dict, error: str) -> None:
    await redis.xadd(
        DEAD_LETTER_KEY,
        {
            "original_id": message_id,
            "data": json.dumps(data),
            "error": error,
            "failed_at": datetime.now().isoformat()
        }
    )


async def retry_message(redis: Redis, data: dict) -> None:
    retry_count = int(data["retry_count"])
    await redis.xadd(
        STREAM_KEY,
        {
            **data,
            "retry_count": str(retry_count + 1)
        }
    )


async def process_batch(
        redis: Redis,
        messages: list
) -> None:
    valid_events = []

    for message_id, data in messages:

        event = parse_message(message_id, data)

        if event is None:
            await send_to_dead_letter(
                redis,
                message_id,
                data,
                error="parse_error"
            )

            await redis.xack(
                STREAM_KEY,
                GROUP_NAME,
                message_id
            )

            continue

        valid_events.append((message_id, data, event))

    if not valid_events:
        return

    try:

        async with AsyncSessionLocal() as session:

            session.add_all([event for _, _, event in valid_events])

            await session.commit()

        await redis.xack(STREAM_KEY, GROUP_NAME, *[message_id for message_id, _, _ in valid_events])

    except Exception as e:
        logger.exception("Failed to save batch")

        for message_id, data, _ in valid_events:
            retry_count = int(data["retry_count"])
            if retry_count >= MAX_RETRIES:

                await send_to_dead_letter(redis, message_id, data, error=f"db_error:{e}")

            else:
                await retry_message(redis, data)

            await redis.xack(
                STREAM_KEY,
                GROUP_NAME,
                message_id
            )


async def run_consumer() -> None:
    redis = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True)

    await ensure_group(redis)

    logger.info("Consumer %s started", CONSUMER_NAME)

    while True:
        try:
            response = await redis.xreadgroup(
                groupname=GROUP_NAME,
                consumername=CONSUMER_NAME,
                streams={
                    STREAM_KEY: ">"
                },
                count=BATCH_SIZE,
                block=BLOCK_MS
            )

            if not response:
                continue

            _, messages = response[0]

            await process_batch(redis, messages)

        except Exception:
            logger.exception("Consumer loop error")

            await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    asyncio.run(run_consumer())
