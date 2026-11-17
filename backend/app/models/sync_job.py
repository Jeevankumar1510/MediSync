import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.integration import APIIntegration
    from app.models.validation import ValidationErrorLog


class SyncJobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class SyncJobType(str, enum.Enum):
    FULL_SYNC = "FULL_SYNC"
    INCREMENTAL = "INCREMENTAL"
    SCHEDULED_POLL = "SCHEDULED_POLL"
    WEBHOOK_TRIGGERED = "WEBHOOK_TRIGGERED"


class SyncJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "synchronization_jobs"

    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    job_type: Mapped[SyncJobType] = mapped_column(
        SQLEnum(SyncJobType, name="sync_job_type_enum"),
        default=SyncJobType.FULL_SYNC,
        nullable=False
    )
    status: Mapped[SyncJobStatus] = mapped_column(
        SQLEnum(SyncJobStatus, name="sync_job_status_enum"),
        default=SyncJobStatus.PENDING,
        nullable=False,
        index=True
    )

    # Metrics
    records_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Retry Strategy
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    integration: Mapped["APIIntegration"] = relationship("APIIntegration", back_populates="sync_jobs")
    validation_errors: Mapped[List["ValidationErrorLog"]] = relationship(
        "ValidationErrorLog",
        back_populates="sync_job",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SyncJob {self.id} [{self.status.value}] for Integration {self.integration_id}>"

