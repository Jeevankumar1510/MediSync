import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.sync_job import SyncJob
    from app.models.patient import PatientRecord
    from app.models.webhook import WebhookEvent


class IntegrationSourceType(str, enum.Enum):
    MOCK_FHIR = "MOCK_FHIR"
    REST_JSON = "REST_JSON"
    OPENMRS = "OPENMRS"
    SYNTHEA = "SYNTHEA"
    HL7_GATEWAY = "HL7_GATEWAY"


class IntegrationAuthType(str, enum.Enum):
    NONE = "NONE"
    API_KEY = "API_KEY"
    BEARER_TOKEN = "BEARER_TOKEN"
    OAUTH2 = "OAUTH2"
    BASIC = "BASIC"


class IntegrationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"
    PAUSED = "PAUSED"


class APIIntegration(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "api_integrations"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_type: Mapped[IntegrationSourceType] = mapped_column(
        SQLEnum(IntegrationSourceType, name="integration_source_type_enum"),
        default=IntegrationSourceType.MOCK_FHIR,
        nullable=False
    )
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    auth_type: Mapped[IntegrationAuthType] = mapped_column(
        SQLEnum(IntegrationAuthType, name="integration_auth_type_enum"),
        default=IntegrationAuthType.NONE,
        nullable=False
    )
    status: Mapped[IntegrationStatus] = mapped_column(
        SQLEnum(IntegrationStatus, name="integration_status_enum"),
        default=IntegrationStatus.ACTIVE,
        nullable=False,
        index=True
    )
    rate_limit_per_min: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    config_params: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=False)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    credential: Mapped[Optional["IntegrationCredential"]] = relationship(
        "IntegrationCredential",
        back_populates="integration",
        uselist=False,
        cascade="all, delete-orphan"
    )
    sync_jobs: Mapped[List["SyncJob"]] = relationship("SyncJob", back_populates="integration", cascade="all, delete-orphan")
    records: Mapped[List["PatientRecord"]] = relationship("PatientRecord", back_populates="integration")
    webhook_events: Mapped[List["WebhookEvent"]] = relationship("WebhookEvent", back_populates="integration")

    def __repr__(self) -> str:
        return f"<APIIntegration {self.name} [{self.source_type.value}] - {self.status.value}>"


class IntegrationCredential(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "integration_credentials"

    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_integrations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    # Store encrypted secrets via AES/Fernet
    encrypted_api_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    encrypted_client_secret: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    token_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    scopes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    encrypted_access_token: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    encrypted_refresh_token: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    integration: Mapped["APIIntegration"] = relationship("APIIntegration", back_populates="credential")

    def __repr__(self) -> str:
        return f"<IntegrationCredential for Integration ID {self.integration_id}>"

