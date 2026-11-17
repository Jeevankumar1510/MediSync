import uuid
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.api.deps import RoleChecker
from app.main import app


def test_password_hashing():
    """Verify that bcrypt hashes passwords and verifies accurately."""
    raw_password = "DoctorSecurePass2026!"
    hashed = get_password_hash(raw_password)
    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_access_and_refresh_tokens():
    """Verify JWT token encoding, role claims, and type isolation."""
    user_id = uuid.uuid4()
    role = UserRole.INTEGRATION_ENGINEER.value

    # 1. Access Token
    access_token = create_access_token(subject=user_id, role=role)
    decoded_access = decode_token(access_token)
    assert decoded_access is not None
    assert decoded_access["sub"] == str(user_id)
    assert decoded_access["role"] == role
    assert decoded_access["type"] == "access"

    # 2. Refresh Token
    refresh_token = create_refresh_token(subject=user_id, role=role)
    decoded_refresh = decode_token(refresh_token)
    assert decoded_refresh is not None
    assert decoded_refresh["sub"] == str(user_id)
    assert decoded_refresh["type"] == "refresh"


def test_user_create_password_validation():
    """Verify password strength validation rules in UserCreate schema."""
    # Fails if too short (< 8 chars)
    with pytest.raises(ValidationError):
        UserCreate(
            email="doc@hospital.com",
            full_name="Dr. Smith",
            password="short",
            role=UserRole.CLINICAL_ANALYST,
        )

    # Fails if missing digit
    with pytest.raises(ValidationError):
        UserCreate(
            email="doc@hospital.com",
            full_name="Dr. Smith",
            password="NoDigitsPasswordHere",
            role=UserRole.CLINICAL_ANALYST,
        )

    # Succeeds with compliant password
    valid = UserCreate(
        email="doc@hospital.com",
        full_name="Dr. Smith",
        password="ValidPassword2026",
        role=UserRole.CLINICAL_ANALYST,
    )
    assert valid.email == "doc@hospital.com"


def test_role_checker_authorization():
    """Verify RoleChecker permits authorized roles and blocks unauthorized roles."""
    admin_checker = RoleChecker([UserRole.ADMIN])
    analyst_checker = RoleChecker([UserRole.ADMIN, UserRole.CLINICAL_ANALYST])

    viewer_user = User(
        email="viewer@test.com",
        hashed_password="hash",
        full_name="Viewer User",
        role=UserRole.VIEWER,
        is_active=True,
    )
    analyst_user = User(
        email="analyst@test.com",
        hashed_password="hash",
        full_name="Analyst User",
        role=UserRole.CLINICAL_ANALYST,
        is_active=True,
    )
    admin_user = User(
        email="admin@test.com",
        hashed_password="hash",
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
    )

    # Viewer should be blocked by analyst_checker (403 Forbidden)
    with pytest.raises(HTTPException) as exc_info:
        analyst_checker(viewer_user)
    assert exc_info.value.status_code == 403

    # Analyst should be allowed by analyst_checker
    assert analyst_checker(analyst_user) == analyst_user

    # Viewer should be blocked by admin_checker
    with pytest.raises(HTTPException) as exc_info:
        admin_checker(viewer_user)
    assert exc_info.value.status_code == 403

    # Admin should be allowed by admin_checker
    assert admin_checker(admin_user) == admin_user


def test_auth_routes_registered():
    """Verify all required authentication routes are mapped in OpenAPI schema."""
    paths = app.openapi()["paths"]
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/refresh" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/auth/register" in paths
    assert "/auth/login" in paths
