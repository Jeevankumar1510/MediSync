import logging
from typing import Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.schemas.user import UserCreate, Token

logger = logging.getLogger("medisync.auth_service")


async def register_user(
    db: AsyncSession,
    user_in: UserCreate,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> User:
    """Registers a new user, hashes their password, and writes an audit log."""
    # Check duplicate email
    query = select(User).where(User.email == user_in.email.lower().strip())
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    # Hash password securely
    hashed_pwd = get_password_hash(user_in.password)

    new_user = User(
        email=user_in.email.lower().strip(),
        hashed_password=hashed_pwd,
        full_name=user_in.full_name.strip(),
        role=user_in.role,
        is_active=True,
        is_superuser=False,
    )
    db.add(new_user)
    await db.flush() # Populate new_user.id before writing audit log

    # Write audit log
    audit_entry = AuditLog(
        user_id=new_user.id,
        action="USER_REGISTERED",
        resource_type="User",
        resource_id=str(new_user.id),
        ip_address=ip_address,
        user_agent=user_agent,
        details={"email": new_user.email, "role": new_user.role.value},
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(new_user)

    logger.info(f"User successfully registered: {new_user.email} (Role: {new_user.role.value})")
    return new_user


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> User:
    """Validates user credentials, records audit trails, and returns the User object."""
    clean_email = email.lower().strip()
    query = select(User).where(User.email == clean_email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        # Record failed login attempt in audit log
        audit_failed = AuditLog(
            user_id=user.id if user else None,
            action="LOGIN_FAILED",
            resource_type="User",
            resource_id=clean_email,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"attempted_email": clean_email, "reason": "invalid_credentials"},
        )
        db.add(audit_failed)
        await db.commit()
        logger.warning(f"Failed authentication attempt for email: {clean_email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    # Record successful login in audit log
    audit_success = AuditLog(
        user_id=user.id,
        action="LOGIN_SUCCESS",
        resource_type="User",
        resource_id=str(user.id),
        ip_address=ip_address,
        user_agent=user_agent,
        details={"email": user.email, "role": user.role.value},
    )
    db.add(audit_success)
    await db.commit()

    logger.info(f"User successfully authenticated: {user.email}")
    return user


def generate_auth_tokens(user: User) -> Token:
    """Generates a synchronized pair of JWT access and refresh tokens."""
    access_token = create_access_token(subject=user.id, role=user.role.value)
    refresh_token = create_refresh_token(subject=user.id, role=user.role.value)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def refresh_user_tokens(db: AsyncSession, refresh_token: str) -> Token:
    """Validates a refresh token and generates fresh access & refresh tokens."""
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed refresh token subject.",
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid UUID in refresh token.",
        )

    user = await db.get(User, user_uuid)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer valid or active.",
        )

    return generate_auth_tokens(user)
