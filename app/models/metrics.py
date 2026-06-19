from datetime import datetime

from pydantic import BaseModel


class TopEvent(BaseModel):
    event_name: str
    count: int


class MetricsResponse(BaseModel):
    period: str
    total_events: int
    rps: float
    error_rate: float
    top_events: list[TopEvent]
    from_time: datetime
    to_time: datetime