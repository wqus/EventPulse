from datetime import datetime, timezone
import uuid
from datetime import timedelta
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.Event import Event

ERROR_KEYWORDS = ["failed", "error", "exception", "timeout"]


def is_error_event(event_name: str) -> bool:
    return any(kw in event_name.lower() for kw in ERROR_KEYWORDS)


PERIOD = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7)
}


def _fill_missing_buckets(points: list[dict], bucket_minutes: int, since: datetime, now: datetime) -> list[dict]:
    points_dict = {p["bucket"]: p for p in points}

    filled_points = []
    current = since.replace(second=0, microsecond=0)

    minutes = current.minute - (current.minute % bucket_minutes)
    current = current.replace(minute=minutes)

    while current <= now:
        bucket_key = current
        if bucket_key in points_dict:
            filled_points.append(points_dict[bucket_key])
        else:
            filled_points.append({
                "bucket": bucket_key,
                "count": 0,
                "error_count": 0
            })
        current += timedelta(minutes=bucket_minutes)

    return filled_points


async def get_metrics(tenant_id: uuid.UUID, period: str, session: AsyncSession) -> dict:
    delta = PERIOD.get(period, timedelta(hours=1))
    now = datetime.now(timezone.utc)
    since = now - delta

    total_result = await session.execute(
        select(func.count()).select_from(Event).where(Event.tenant_id == tenant_id).where(Event.timestamp >= since)
    )

    total = total_result.scalar()

    top_result = await session.execute(
        select(Event.event_name, func.count())
        .where(Event.tenant_id == tenant_id)
        .where(Event.timestamp >= since)
        .group_by(Event.event_name)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_events = [{"event_name": row[0], "count": row[1]} for row in top_result.all()]

    error_result = await session.execute(
        select(func.count())
        .select_from(Event)
        .where(Event.tenant_id == tenant_id)
        .where(Event.timestamp >= since)
        .where(
            func.lower(Event.event_name).contains("failed") |
            func.lower(Event.event_name).contains("error") |
            func.lower(Event.event_name).contains("exception") |
            func.lower(Event.event_name).contains("timeout")
        )
    )
    error_count = error_result.scalar()

    seconds = delta.total_seconds()
    rps = round(total / seconds, 3) if total > 0 else 0.0
    error_rate = round(error_count / total, 3) if total > 0 else 0.0

    return {
        "period": period,
        "total_events": total,
        "rps": rps,
        "error_rate": error_rate,
        "top_events": top_events,
        "from_time": since,
        "to_time": now,
    }


BUCKET_MAP = {
    "1h": timedelta(minutes=5),
    "24h": timedelta(hours=1),
    "7d": timedelta(hours=12),
}

BUCKET_LABEL = {
    "1h": "5m",
    "24h": "1h",
    "7d": "12h",
}


async def get_timeseries(tenant_id: uuid.UUID, period: str, session: AsyncSession) -> dict:
    delta = PERIOD.get(period, timedelta(hours=1))
    bucket = BUCKET_MAP.get(period, "5 minutes")
    now = datetime.now(timezone.utc)
    since = now - delta

    result = await session.execute(
        text("""
        SELECT time_bucket(:bucket, "timestamp") AS bucket,
        COUNT(*) AS count,
        COUNT(*) FILTER(
            WHERE event_name ILIKE '%failed%'
            OR event_name ILIKE '%error%'
            OR event_name ILIKE '%exception%'
            OR event_name ILIKE '%timeout%') AS error_count
        FROM events
        WHERE tenant_id = :tenant_id
        AND timestamp >= :since
        AND timestamp <= :now
        GROUP BY bucket
        ORDER BY bucket ASC"""), {
            "bucket": bucket,
            "tenant_id": str(tenant_id),
            "since": since,
            "now": now
        }
    )

    points = [
        {"bucket": row[0], "count": row[1], "error_count": row[2]} for row in result.all()
    ]
    bucket_minutes = 5 if period == "1h" else 60 if period == "24h" else 720
    points = _fill_missing_buckets(points, bucket_minutes, since, now)

    return {
        "period": period,
        "bucket_size": BUCKET_LABEL.get(period, "5m"),
        "points": points
    }
