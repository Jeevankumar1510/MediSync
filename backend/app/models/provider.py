from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.patient import PatientRecord


class HealthcareProvider(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "healthcare_providers"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    npi: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True, nullable=True) # National Provider Identifier
    organization_type: Mapped[str] = mapped_column(String(100), default="HOSPITAL", nullable=False) # HOSPITAL, CLINIC, LAB, PHARMACY
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    records: Mapped[List["PatientRecord"]] = relationship("PatientRecord", back_populates="provider")

    def __repr__(self) -> str:
        return f"<HealthcareProvider {self.name} (NPI: {self.npi})>"

