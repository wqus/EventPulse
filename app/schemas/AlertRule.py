import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=255)
    threshold: int = Field(..., gt=0)
    window_seconds: int = Field(..., ge=60, le=86400)


class AlertRuleResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    event_name: str
    threshold: int
    window_seconds: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True