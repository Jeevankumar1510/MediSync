import enum
from typing import TYPE_CHECKING, List
from sqlalchemy import String, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.chat import Conversation
    from app.models.audit import AuditLog
    from app.models.ai_analysis import AIAnalysis


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    INTEGRATION_ENGINEER = "INTEGRATION_ENGINEER"
    CLINICAL_ANALYST = "CLINICAL_ANALYST"
    VIEWER = "VIEWER"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role_enum"),
        default=UserRole.VIEWER,
        nullable=False,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="uploader", cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")
    reviewed_analyses: Mapped[List["AIAnalysis"]] = relationship("AIAnalysis", back_populates="reviewed_by_user")

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"

