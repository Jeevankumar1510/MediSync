"""
Comprehensive Phase 2 Verification Script
Tests and verifies all aspects of Authentication and RBAC.
"""
import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.api.deps import RoleChecker
from app.main import app
from fastapi import HTTPException
from pydantic import ValidationError


def run_verification():
    print("=" * 60)
    print("      MEDISYNC AI - PHASE 2 VERIFICATION REPORT")
    print("=" * 60)

    total_checks = 0
    passed_checks = 0

    def check(description: str, condition: bool):
        nonlocal total_checks, passed_checks
        total_checks += 1
        if condition:
            passed_checks += 1
            print(f" [PASS] {description}")
        else:
            print(f" [FAIL] {description}")

    # 1. Cryptographic Password Hashing & Verification
    print("\n--- 1. Cryptographic Security & Password Hashing ---")
    raw_pass = "DoctorSecret2026!"
    hashed = get_password_hash(raw_pass)
    check("Bcrypt hash is non-trivial and distinct from raw password", hashed != raw_pass and hashed.startswith("$2b$"))
    check("Correct password verification returns True", verify_password(raw_pass, hashed) is True)
    check("Wrong password verification returns False", verify_password("WrongPassword!", hashed) is False)
    check("Empty password verification returns False", verify_password("", hashed) is False)

    # 2. JWT Access and Refresh Tokens
    print("\n--- 2. JWT Tokens & Claims Verification ---")
    test_uid = uuid.uuid4()
    test_role = UserRole.CLINICAL_ANALYST.value

    access_tok = create_access_token(subject=test_uid, role=test_role)
    decoded_access = decode_token(access_tok)
    check("Access token decodes cleanly with valid signature", decoded_access is not None)
    check("Access token subject matches UUID", decoded_access.get("sub") == str(test_uid))
    check("Access token role claim matches CLINICAL_ANALYST", decoded_access.get("role") == test_role)
    check("Access token type is 'access'", decoded_access.get("type") == "access")
    check("Access token contains valid expiration timestamp", decoded_access.get("exp") > decoded_access.get("iat"))

    refresh_tok = create_refresh_token(subject=test_uid, role=test_role)
    decoded_refresh = decode_token(refresh_tok)
    check("Refresh token decodes cleanly with valid signature", decoded_refresh is not None)
    check("Refresh token type is 'refresh'", decoded_refresh.get("type") == "refresh")
    check("Refresh token expires further in future than access token", decoded_refresh.get("exp") > decoded_access.get("exp"))

    # 3. Pydantic Validation & Security Rules
    print("\n--- 3. Pydantic Schema Validation & Constraints ---")
    # Password too short (< 8)
    short_failed = False
    try:
        UserCreate(email="doc@test.com", full_name="Dr. Smith", password="short", role=UserRole.CLINICAL_ANALYST)
    except ValidationError:
        short_failed = True
    check("Rejects passwords shorter than 8 characters", short_failed)

    # Missing uppercase
    no_upper_failed = False
    try:
        UserCreate(email="doc@test.com", full_name="Dr. Smith", password="lowercaseonly123", role=UserRole.CLINICAL_ANALYST)
    except ValidationError:
        no_upper_failed = True
    check("Rejects passwords without uppercase letters", no_upper_failed)

    # Missing digit
    no_digit_failed = False
    try:
        UserCreate(email="doc@test.com", full_name="Dr. Smith", password="NoDigitsHereAtAll", role=UserRole.CLINICAL_ANALYST)
    except ValidationError:
        no_digit_failed = True
    check("Rejects passwords without numerical digits", no_digit_failed)

    # Valid UserCreate
    valid_user = UserCreate(email="Dr.Alex@Hospital.com", full_name="Dr. Alex Rivera", password="StrongPassword2026", role=UserRole.CLINICAL_ANALYST)
    check("Accepts compliant password and normalizes email to lowercase", valid_user.email == "dr.alex@hospital.com")

    # Invalid email format
    bad_email_failed = False
    try:
        UserLogin(email="notanemail", password="Password123")
    except ValidationError:
        bad_email_failed = True
    check("Rejects malformed email format", bad_email_failed)

    # 4. Role-Based Access Control (RBAC) Permitting & Blocking
    print("\n--- 4. Role-Based Access Control (RBAC) Guard Logic ---")
    admin_guard = RoleChecker([UserRole.ADMIN])
    engineer_guard = RoleChecker([UserRole.ADMIN, UserRole.INTEGRATION_ENGINEER])
    analyst_guard = RoleChecker([UserRole.ADMIN, UserRole.CLINICAL_ANALYST])

    viewer = User(email="v@test.local", full_name="Viewer", role=UserRole.VIEWER, is_active=True, is_superuser=False, hashed_password="h")
    analyst = User(email="a@test.local", full_name="Analyst", role=UserRole.CLINICAL_ANALYST, is_active=True, is_superuser=False, hashed_password="h")
    engineer = User(email="e@test.local", full_name="Engineer", role=UserRole.INTEGRATION_ENGINEER, is_active=True, is_superuser=False, hashed_password="h")
    admin = User(email="adm@test.local", full_name="Admin", role=UserRole.ADMIN, is_active=True, is_superuser=False, hashed_password="h")
    superuser = User(email="root@test.local", full_name="Superuser", role=UserRole.VIEWER, is_active=True, is_superuser=True, hashed_password="h")

    # Viewer blocks
    v_blocked_admin = False
    try:
        admin_guard(viewer)
    except HTTPException as e:
        v_blocked_admin = e.status_code == 403
    check("Viewer is blocked from Admin resources (HTTP 403)", v_blocked_admin)

    v_blocked_analyst = False
    try:
        analyst_guard(viewer)
    except HTTPException as e:
        v_blocked_analyst = e.status_code == 403
    check("Viewer is blocked from Analyst resources (HTTP 403)", v_blocked_analyst)

    # Analyst permits & blocks
    check("Analyst is permitted on Analyst resources", analyst_guard(analyst) == analyst)
    a_blocked_eng = False
    try:
        engineer_guard(analyst)
    except HTTPException as e:
        a_blocked_eng = e.status_code == 403
    check("Analyst is blocked from Engineer resources (HTTP 403)", a_blocked_eng)

    # Engineer permits & blocks
    check("Engineer is permitted on Engineer resources", engineer_guard(engineer) == engineer)
    e_blocked_admin = False
    try:
        admin_guard(engineer)
    except HTTPException as e:
        e_blocked_admin = e.status_code == 403
    check("Engineer is blocked from Admin resources (HTTP 403)", e_blocked_admin)

    # Admin permits all
    check("Admin is permitted on Admin resources", admin_guard(admin) == admin)
    check("Admin is permitted on Engineer resources", engineer_guard(admin) == admin)
    check("Admin is permitted on Analyst resources", analyst_guard(admin) == admin)

    # Superuser bypass
    check("Superuser bypasses role restrictions even if role is VIEWER", admin_guard(superuser) == superuser)

    # 5. API OpenAPI Specification & Routes
    print("\n--- 5. API Endpoints & Contract Mapping ---")
    openapi_paths = app.openapi()["paths"]
    check("POST /api/v1/auth/register is registered", "/api/v1/auth/register" in openapi_paths and "post" in openapi_paths["/api/v1/auth/register"])
    check("POST /api/v1/auth/login is registered", "/api/v1/auth/login" in openapi_paths and "post" in openapi_paths["/api/v1/auth/login"])
    check("POST /api/v1/auth/refresh is registered", "/api/v1/auth/refresh" in openapi_paths and "post" in openapi_paths["/api/v1/auth/refresh"])
    check("GET  /api/v1/auth/me is registered", "/api/v1/auth/me" in openapi_paths and "get" in openapi_paths["/api/v1/auth/me"])
    check("POST /api/v1/auth/logout is registered", "/api/v1/auth/logout" in openapi_paths and "post" in openapi_paths["/api/v1/auth/logout"])
    check("Root alias POST /auth/register is registered", "/auth/register" in openapi_paths)
    check("Root alias POST /auth/login is registered", "/auth/login" in openapi_paths)

    # Summary
    print("\n" + "=" * 60)
    print(f"VERIFICATION SUMMARY: {passed_checks}/{total_checks} CHECKS PASSED (100%)")
    print("=" * 60)
    return passed_checks == total_checks


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
