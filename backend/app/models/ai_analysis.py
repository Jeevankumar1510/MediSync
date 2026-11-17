import enum
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import String, Float, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class AnalysisType(str, enum.Enum):
    DATA_QUALITY = "DATA_QUALITY"
    ANOMALY_DETECTION = "ANOMALY_DETECTION"
    FIELD_MAPPING = "FIELD_MAPPING"
    SYNTAX_VALIDATION = "SYNTAX_VALIDATION"


class AnalysisReviewStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_APPLIED = "AUTO_APPLIED"


class AIAnalysis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ai_analyses"

    target_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True) # PATIENT_RECORD, SYNC_JOB, INTEGRATION
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    analysis_type: Mapped[AnalysisType] = mapped_column(
        SQLEnum(AnalysisType, name="analysis_type_enum"),
        default=AnalysisType.DATA_QUALITY,
        nullable=False,
        index=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    findings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[AnalysisReviewStatus] = mapped_column(
        SQLEnum(AnalysisReviewStatus, name="analysis_review_status_enum"),
        default=AnalysisReviewStatus.PENDING_REVIEW,
        nullable=False,
        index=True
    )
    reviewed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    reviewed_by_user: Mapped[Optional["User"]] = relationship("User", back_populates="reviewed_analyses")

    def __repr__(self) -> str:
        return f"<AIAnalysis {self.analysis_type.value} [conf={self.confidence_score}] - {self.status.value}>"

