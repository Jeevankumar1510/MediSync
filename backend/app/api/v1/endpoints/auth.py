from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    RefreshTokenRequest,
)
from app.services import auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new healthcare user account with role assignment and hashed password.",
)
async def register(
    request: Request,
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    user = await auth_service.register_user(
        db=db,
        user_in=user_in,
        ip_address=client_ip,
        user_agent=user_agent
    )
    return user


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User Login & Token Issuance",
    description="Authenticates credentials and returns a synchronized pair of JWT access and refresh tokens.",
)
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    user = await auth_service.authenticate_user(
        db=db,
        email=credentials.email,
        password=credentials.password,
        ip_address=client_ip,
        user_agent=user_agent
    )
    return auth_service.generate_auth_tokens(user)


@router.post(
    "/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Exchanges a valid refresh token for a fresh access and refresh token pair.",
)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    return await auth_service.refresh_user_tokens(db=db, refresh_token=payload.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns the profile and role details of the currently authenticated user.",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    return current_user


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Logs out the user and records an audit log entry for session termination.",
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    audit_entry = AuditLog(
        user_id=current_user.id,
        action="USER_LOGOUT",
        resource_type="User",
        resource_id=str(current_user.id),
        ip_address=client_ip,
        user_agent=user_agent,
        details={"email": current_user.email},
    )
    db.add(audit_entry)
    await db.commit()

    return {"message": "Successfully logged out."}
