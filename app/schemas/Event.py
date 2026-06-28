from typing import Any

from pydantic import BaseModel, field_validator, Field
from datetime import datetime, timezone, tzinfo

class EventIngest(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("event_name")
    @classmethod
    def validate_event_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("event_name cannot be empty")
        return value

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo = timezone.utc)
        else:
            value = value.astimezone(timezone.utc)

        if value > datetime.now(timezone.utc):
            raise ValueError("timestamp cannot be in the future")

        return value


class EventResponse(BaseModel):
    status: str = "accepted"