from datetime import date
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import String, Boolean, Date, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.provider import HealthcareProvider
    from app.models.integration import APIIntegration
    from app.models.validation import ValidationErrorLog


class Patient(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "patients"

    # Medical Record Number - globally unique identifier across health systems
    mrn: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True) # male, female, other, unknown
    contact_info: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=True)
    address: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    records: Mapped[List["PatientRecord"]] = relationship(
        "PatientRecord",
        back_populates="patient",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Patient MRN: {self.mrn} ({self.first_name} {self.last_name})>"


class PatientRecord(Base, UUIDMixin, TimestampMixin):
    """
    Normalized FHIR-compatible Clinical Resource Record (e.g. Observation, Condition, Encounter).
    Stores both the original raw vendor JSON and the normalized FHIR JSON for full auditability.
    """
    __tablename__ = "patient_records"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    provider_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("healthcare_providers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    integration_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_integrations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # FHIR Classification
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # e.g. Observation, Condition
    fhir_version: Mapped[str] = mapped_column(String(10), default="R4", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)

    # SHA-256 Checksum of the raw payload for idempotency & deduplication
    checksum: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)

    # Payloads
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    normalized_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="records")
    provider: Mapped[Optional["HealthcareProvider"]] = relationship("HealthcareProvider", back_populates="records")
    integration: Mapped[Optional["APIIntegration"]] = relationship("APIIntegration", back_populates="records")
    validation_errors: Mapped[List["ValidationErrorLog"]] = relationship(
        "ValidationErrorLog",
        back_populates="record",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_patient_records_type_status", "resource_type", "status"),
    )

    def __repr__(self) -> str:
        return f"<PatientRecord {self.resource_type} for Patient {self.patient_id} [{self.status}]>"

