import uuid
import enum
from datetime import datetime

from sqlalchemy import String, Enum, Boolean, DateTime, func
from sqlalchemy.orm import Mapped
from sqlalchemy.testing.schema import mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class Plan(enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Tenant(Base):
    __tablename__ = 'tenants'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[Plan] = mapped_column(
        Enum(
            Plan,
            values_callable=lambda enum_cls: [e.value for e in enum_cls]
        ),
        nullable=False,
        default=Plan.FREE)
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

