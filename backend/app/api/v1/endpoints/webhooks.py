from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_engineer
from app.database import get_db
from app.models.user import User
from app.schemas.webhook import (
    WebhookEventIngest,
    WebhookIngestResponse,
    WebhookEventResponse,
    WebhookEventListResponse,
)
from app.services import webhook_service

router = APIRouter()


@router.post(
    "/events",
    response_model=WebhookIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive Healthcare Webhook Event",
    description="Asynchronously receives and verifies webhook event notifications from external EHRs, applying idempotency deduplication.",
)
async def receive_webhook(
    request: Request,
    event_in: WebhookEventIngest,
    x_signature_sha256: Optional[str] = Header(None, alias="X-Signature-SHA256"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_db),
):
    signature = x_signature_sha256 or x_hub_signature_256
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await webhook_service.receive_webhook_event(
        db=db,
        source=event_in.source,
        event_type=event_in.event_type,
        payload=event_in.payload,
        event_id=event_in.event_id,
        signature=signature,
        integration_id=event_in.integration_id,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.get(
    "/events",
    response_model=WebhookEventListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Webhook Events & Logs",
    description="Retrieves a paginated list of inbound webhook events with source, status, and retry statistics.",
)
async def list_webhook_events(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    source: Optional[str] = Query(None, description="Filter by source system (e.g. Epic, Cerner)"),
    status: Optional[str] = Query(None, description="Filter by status: RECEIVED, PROCESSING, PROCESSED, FAILED, IGNORED"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    return await webhook_service.list_webhook_events(
        db=db,
        page=page,
        size=size,
        source=source,
        status_filter=status,
    )


@router.post(
    "/events/{event_id}/retry",
    response_model=WebhookEventResponse,
    status_code=status.HTTP_200_OK,
    summary="Retry Webhook Event Processing",
    description="Manually re-enqueues a failed or unhandled webhook event for background re-processing.",
)
async def retry_webhook_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    return await webhook_service.retry_webhook_event(
        db=db,
        event_id=event_id,
    )
