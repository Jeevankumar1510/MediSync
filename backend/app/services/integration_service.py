import logging
from typing import List, Optional, Tuple, Dict, Any
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt_secret, decrypt_secret
from app.models.integration import (
    APIIntegration,
    IntegrationCredential,
    IntegrationSourceType,
    IntegrationAuthType,
    IntegrationStatus,
)
from app.models.sync_job import SyncJob, SyncJobStatus, SyncJobType
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.integration import (
    APIIntegrationCreate,
    APIIntegrationUpdate,
    APIIntegrationResponse,
    IntegrationCredentialResponse,
    ConnectionTestResult,
    SyncTriggerResponse,
)
from app.services.integrations.fhir_client import FHIRClient
from app.services.integrations.vendor_client import VendorRESTClient

logger = logging.getLogger("medisync.integration_service")


def format_credential_response(cred: Optional[IntegrationCredential]) -> Optional[IntegrationCredentialResponse]:
    """Transforms stored encrypted credentials into a safe redacted summary."""
    if not cred:
        return None
    return IntegrationCredentialResponse(
        id=cred.id,
        client_id=cred.client_id,
        token_url=cred.token_url,
        scopes=cred.scopes,
        has_api_key=bool(cred.encrypted_api_key),
        has_client_secret=bool(cred.encrypted_client_secret),
        has_access_token=bool(cred.encrypted_access_token),
        token_expires_at=cred.token_expires_at,
    )


async def list_integrations(db: AsyncSession) -> List[APIIntegrationResponse]:
    """Retrieves all registered external healthcare integrations with credential metadata."""
    query = select(APIIntegration).options(selectinload(APIIntegration.credential)).order_by(APIIntegration.created_at.desc())
    res = await db.execute(query)
    integrations = res.scalars().all()

    output: List[APIIntegrationResponse] = []
    for item in integrations:
        resp = APIIntegrationResponse.model_validate(item)
        resp.credential = format_credential_response(item.credential)
        output.append(resp)
    return output


async def get_integration_by_id(db: AsyncSession, integration_id: uuid.UUID) -> APIIntegration:
    """Retrieves a single integration with loaded credential relationships."""
    query = select(APIIntegration).where(APIIntegration.id == integration_id).options(selectinload(APIIntegration.credential))
    res = await db.execute(query)
    integration = res.scalar_one_or_none()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration with ID '{integration_id}' was not found.",
        )
    return integration


async def create_integration(
    db: AsyncSession,
    integration_in: APIIntegrationCreate,
    current_user: Optional[User] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> APIIntegrationResponse:
    """Registers a healthcare API integration and securely vaults encrypted credentials."""
    # Enforce unique integration name
    existing_q = select(APIIntegration).where(APIIntegration.name == integration_in.name.strip())
    existing_res = await db.execute(existing_q)
    if existing_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An integration named '{integration_in.name}' already exists.",
        )

    integration = APIIntegration(
        name=integration_in.name.strip(),
        description=integration_in.description,
        source_type=integration_in.source_type,
        base_url=integration_in.base_url.strip(),
        auth_type=integration_in.auth_type,
        status=integration_in.status,
        rate_limit_per_min=integration_in.rate_limit_per_min,
        timeout_seconds=integration_in.timeout_seconds,
        config_params=integration_in.config_params or {},
    )
    db.add(integration)
    await db.flush()

    # Store encrypted credentials if provided
    cred_response: Optional[IntegrationCredentialResponse] = None
    if integration_in.credentials:
        c_in = integration_in.credentials
        enc_api_key = encrypt_secret(c_in.api_key) if c_in.api_key else None
        enc_secret = encrypt_secret(c_in.client_secret) if c_in.client_secret else None

        credential = IntegrationCredential(
            integration_id=integration.id,
            encrypted_api_key=enc_api_key,
            encrypted_client_secret=enc_secret,
            client_id=c_in.client_id,
            token_url=c_in.token_url,
            scopes=c_in.scopes,
        )
        db.add(credential)
        await db.flush()
        cred_response = format_credential_response(credential)

    if current_user:
        audit_entry = AuditLog(
            user_id=current_user.id,
            action="INTEGRATION_CREATE",
            resource_type="APIIntegration",
            resource_id=str(integration.id),
            ip_address=ip_address,
            user_agent=user_agent,
            details={"name": integration.name, "source_type": integration.source_type.value},
        )
        db.add(audit_entry)

    await db.commit()
    await db.refresh(integration)

    resp = APIIntegrationResponse.model_validate(integration)
    resp.credential = cred_response
    logger.info(f"Registered API Integration: {integration.name} [{integration.source_type.value}]")
    return resp


async def update_integration(
    db: AsyncSession,
    integration_id: uuid.UUID,
    integration_in: APIIntegrationUpdate,
    current_user: Optional[User] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> APIIntegrationResponse:
    """Updates integration metadata and re-encrypts updated credential secrets."""
    integration = await get_integration_by_id(db, integration_id)

    update_dict = integration_in.model_dump(exclude_unset=True)
    credentials_update = update_dict.pop("credentials", None)

    for field, val in update_dict.items():
        setattr(integration, field, val)

    if credentials_update:
        # Fetch or create credential record
        cred = integration.credential
        if not cred:
            cred = IntegrationCredential(integration_id=integration.id)
            db.add(cred)

        if "api_key" in credentials_update and credentials_update["api_key"]:
            cred.encrypted_api_key = encrypt_secret(credentials_update["api_key"])
        if "client_secret" in credentials_update and credentials_update["client_secret"]:
            cred.encrypted_client_secret = encrypt_secret(credentials_update["client_secret"])
        if "client_id" in credentials_update:
            cred.client_id = credentials_update["client_id"]
        if "token_url" in credentials_update:
            cred.token_url = credentials_update["token_url"]
        if "scopes" in credentials_update:
            cred.scopes = credentials_update["scopes"]

    if current_user:
        audit_entry = AuditLog(
            user_id=current_user.id,
            action="INTEGRATION_UPDATE",
            resource_type="APIIntegration",
            resource_id=str(integration.id),
            ip_address=ip_address,
            user_agent=user_agent,
            details={"updated_fields": list(integration_in.model_dump(exclude_unset=True).keys())},
        )
        db.add(audit_entry)

    await db.commit()
    await db.refresh(integration)

    resp = APIIntegrationResponse.model_validate(integration)
    resp.credential = format_credential_response(integration.credential)
    return resp


async def delete_integration(
    db: AsyncSession,
    integration_id: uuid.UUID,
    current_user: Optional[User] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Deletes an integration and cascades credential removal."""
    integration = await get_integration_by_id(db, integration_id)
    name = integration.name
    await db.delete(integration)

    if current_user:
        audit_entry = AuditLog(
            user_id=current_user.id,
            action="INTEGRATION_DELETE",
            resource_type="APIIntegration",
            resource_id=str(integration_id),
            ip_address=ip_address,
            user_agent=user_agent,
            details={"deleted_name": name},
        )
        db.add(audit_entry)

    await db.commit()
    logger.warning(f"Deleted integration {integration_id} ({name})")


async def test_integration_connection(db: AsyncSession, integration_id: uuid.UUID) -> ConnectionTestResult:
    """Decrypts credentials and conducts a diagnostic handshake with the external healthcare service."""
    integration = await get_integration_by_id(db, integration_id)

    # Prepare decrypted authentication headers
    auth_headers: Dict[str, str] = {}
    if integration.credential:
        if integration.auth_type == IntegrationAuthType.API_KEY and integration.credential.encrypted_api_key:
            raw_key = decrypt_secret(integration.credential.encrypted_api_key)
            auth_headers["X-API-Key"] = raw_key or ""
        elif integration.auth_type == IntegrationAuthType.BEARER_TOKEN and integration.credential.encrypted_access_token:
            raw_token = decrypt_secret(integration.credential.encrypted_access_token)
            auth_headers["Authorization"] = f"Bearer {raw_token}"

    # Select client adapter
    if integration.source_type == IntegrationSourceType.MOCK_FHIR or "fhir" in integration.base_url.lower():
        client = FHIRClient(
            base_url=integration.base_url,
            timeout_seconds=integration.timeout_seconds,
            rate_limit_per_min=integration.rate_limit_per_min,
            auth_headers=auth_headers,
        )
    else:
        client = VendorRESTClient(
            base_url=integration.base_url,
            timeout_seconds=integration.timeout_seconds,
            rate_limit_per_min=integration.rate_limit_per_min,
            auth_headers=auth_headers,
        )

    res = await client.test_connection()
    return ConnectionTestResult(**res)


async def trigger_sync_job(
    db: AsyncSession,
    integration_id: uuid.UUID,
    job_type: SyncJobType = SyncJobType.FULL_SYNC,
    current_user: Optional[User] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SyncTriggerResponse:
    """Initializes a background synchronization job in PENDING state."""
    integration = await get_integration_by_id(db, integration_id)

    job = SyncJob(
        integration_id=integration.id,
        job_type=job_type,
        status=SyncJobStatus.PENDING,
        records_fetched=0,
        records_processed=0,
        records_failed=0,
        retry_count=0,
    )
    db.add(job)
    await db.flush()

    if current_user:
        audit_entry = AuditLog(
            user_id=current_user.id,
            action="SYNC_TRIGGER",
            resource_type="SyncJob",
            resource_id=str(job.id),
            ip_address=ip_address,
            user_agent=user_agent,
            details={"integration_name": integration.name, "job_type": job.job_type.value},
        )
        db.add(audit_entry)

    await db.commit()
    await db.refresh(job)

    logger.info(f"Triggered SyncJob {job.id} for integration '{integration.name}'")
    return SyncTriggerResponse(
        job_id=job.id,
        integration_id=integration.id,
        status=job.status.value,
        message=f"Synchronization job {job.id} successfully queued for '{integration.name}'.",
    )
