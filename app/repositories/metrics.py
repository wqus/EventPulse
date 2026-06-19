from datetime import datetime, timezone
import uuid
from datetime import timedelta
from sqlalchemy import select, func
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