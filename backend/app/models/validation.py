import enum
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.patient import PatientRecord
    from app.models.sync_job import SyncJob


class ValidationSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationErrorType(str, enum.Enum):
    MISSING_FIELD = "MISSING_FIELD"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    INVALID_FHIR = "INVALID_FHIR"
    DUPLICATE = "DUPLICATE"
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"


class ValidationErrorLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "validation_error_logs"

    record_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patient_records.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    sync_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("synchronization_jobs.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    field_path: Mapped[str] = mapped_column(String(255), nullable=False)
    error_type: Mapped[ValidationErrorType] = mapped_column(
        SQLEnum(ValidationErrorType, name="validation_error_type_enum"),
        default=ValidationErrorType.INVALID_FHIR,
        nullable=False,
        index=True
    )
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    severity: Mapped[ValidationSeverity] = mapped_column(
        SQLEnum(ValidationSeverity, name="validation_severity_enum"),
        default=ValidationSeverity.WARNING,
        nullable=False,
        index=True
    )

    # Relationships
    record: Mapped[Optional["PatientRecord"]] = relationship("PatientRecord", back_populates="validation_errors")
    sync_job: Mapped[Optional["SyncJob"]] = relationship("SyncJob", back_populates="validation_errors")

    def __repr__(self) -> str:
        return f"<ValidationErrorLog {self.error_type.value} on {self.field_path} ({self.severity.value})>"

