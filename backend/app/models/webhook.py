import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.integration import APIIntegration


class WebhookStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    IGNORED = "IGNORED"


class WebhookEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "webhook_events"

    integration_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_integrations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # External idempotency identifier (e.g. Stripe/Epic event ID)
    event_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    signature: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[WebhookStatus] = mapped_column(
        SQLEnum(WebhookStatus, name="webhook_status_enum"),
        default=WebhookStatus.RECEIVED,
        nullable=False,
        index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    integration: Mapped[Optional["APIIntegration"]] = relationship("APIIntegration", back_populates="webhook_events")

    __table_args__ = (
        Index("idx_webhook_source_event_id", "source", "event_id"),
    )

    def __repr__(self) -> str:
        return f"<WebhookEvent {self.id} [{self.source}:{self.event_type}] - {self.status.value}>"

