from typing import List
import uuid
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_engineer, require_admin
from app.database import get_db
from app.models.user import User
from app.models.sync_job import SyncJobType
from app.schemas.integration import (
    APIIntegrationCreate,
    APIIntegrationUpdate,
    APIIntegrationResponse,
    ConnectionTestResult,
    SyncTriggerResponse,
)
from app.services import integration_service

router = APIRouter()


@router.get(
    "",
    response_model=List[APIIntegrationResponse],
    status_code=status.HTTP_200_OK,
    summary="List API Integrations",
    description="Lists all registered healthcare API integrations (FHIR, REST, HL7) with redacted credential statuses.",
)
async def list_integrations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    return await integration_service.list_integrations(db=db)


@router.post(
    "",
    response_model=APIIntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register API Integration",
    description="Registers a new external healthcare data source and securely vaults credentials with AES/Fernet encryption.",
)
async def create_integration(
    request: Request,
    integration_in: APIIntegrationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await integration_service.create_integration(
        db=db,
        integration_in=integration_in,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.get(
    "/{integration_id}",
    response_model=APIIntegrationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Integration Details",
    description="Retrieves configuration parameters and connection status for a specific integration UUID.",
)
async def get_integration(
    integration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    integration = await integration_service.get_integration_by_id(db=db, integration_id=integration_id)
    resp = APIIntegrationResponse.model_validate(integration)
    resp.credential = integration_service.format_credential_response(integration.credential)
    return resp


@router.put(
    "/{integration_id}",
    response_model=APIIntegrationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Integration Configuration",
    description="Modifies endpoint parameters, rate limits, timeouts, or updates encrypted API credentials.",
)
async def update_integration(
    request: Request,
    integration_id: uuid.UUID,
    integration_in: APIIntegrationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await integration_service.update_integration(
        db=db,
        integration_id=integration_id,
        integration_in=integration_in,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.delete(
    "/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Integration",
    description="Removes an integration and purges vaulted credentials. Strictly restricted to ADMIN role.",
)
async def delete_integration(
    request: Request,
    integration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await integration_service.delete_integration(
        db=db,
        integration_id=integration_id,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    return None


@router.post(
    "/{integration_id}/test-connection",
    response_model=ConnectionTestResult,
    status_code=status.HTTP_200_OK,
    summary="Test Integration Handshake",
    description="Performs an end-to-end diagnostic ping against the external API endpoint and returns latency.",
)
async def test_connection(
    integration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    return await integration_service.test_integration_connection(db=db, integration_id=integration_id)


@router.post(
    "/{integration_id}/sync",
    response_model=SyncTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Synchronization Job",
    description="Queues a background synchronization job for this healthcare integration.",
)
async def trigger_sync(
    request: Request,
    integration_id: uuid.UUID,
    job_type: SyncJobType = SyncJobType.FULL_SYNC,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await integration_service.trigger_sync_job(
        db=db,
        integration_id=integration_id,
        job_type=job_type,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )
