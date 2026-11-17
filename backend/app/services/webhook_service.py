from datetime import datetime, timezone
import logging
from typing import Dict, Any, List, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_sync_db
from app.models.webhook import WebhookEvent, WebhookStatus
from app.models.patient import Patient, PatientRecord
from app.models.audit import AuditLog
from app.schemas.webhook import (
    WebhookIngestResponse,
    WebhookEventResponse,
    WebhookEventListResponse,
)
from app.services.patient_service import compute_payload_checksum
from app.services.normalization.normalizer import (
    detect_resource_type,
    normalize_patient,
    normalize_observation,
    normalize_condition,
)

logger = logging.getLogger("medisync.webhook_service")


async def receive_webhook_event(
    db: AsyncSession,
    source: str,
    event_type: str,
    payload: Dict[str, Any],
    event_id: Optional[str] = None,
    signature: Optional[str] = None,
    integration_id: Optional[uuid.UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> WebhookIngestResponse:
    """
    Ingests an incoming webhook event.
    Applies strict idempotency filtering to prevent duplicate processing of the same event ID.
    """
    clean_source = source.strip()
    clean_type = event_type.strip().lower()

    # Generate deterministic or random idempotency key if external system omitted it
    if not event_id:
        checksum = compute_payload_checksum(payload)
        event_id = f"evt_{clean_source.lower()}_{checksum[:16]}"

    # Idempotency Filter Check
    existing_q = select(WebhookEvent).where(
        WebhookEvent.source == clean_source,
        WebhookEvent.event_id == event_id,
    )
    existing_res = await db.execute(existing_q)
    existing_event = existing_res.scalar_one_or_none()

    if existing_event:
        logger.info(f"Duplicate webhook event detected and filtered: {clean_source}:{event_id}")
        return WebhookIngestResponse(
            event_id=event_id,
            status=existing_event.status.value,
            message="Duplicate event acknowledged via idempotency filter.",
            idempotent_duplicate=True,
        )

    # Register new webhook event
    event = WebhookEvent(
        source=clean_source,
        event_type=clean_type,
        event_id=event_id,
        integration_id=integration_id,
        signature=signature,
        payload=payload,
        status=WebhookStatus.RECEIVED,
        retry_count=0,
    )
    db.add(event)
    await db.flush()

    # Write audit log
    audit_entry = AuditLog(
        user_id=None,
        action="WEBHOOK_RECEIVED",
        resource_type="WebhookEvent",
        resource_id=str(event.id),
        ip_address=ip_address,
        user_agent=user_agent,
        details={"source": clean_source, "event_type": clean_type, "event_id": event_id},
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(event)

    # Dispatch to background Celery worker or process inline if worker offline
    try:
        from app.tasks.webhook_tasks import process_webhook_event_task
        process_webhook_event_task.delay(str(event.id))
    except Exception as dispatch_err:
        logger.warning(f"Celery dispatch unavailable ({dispatch_err}). Processing webhook synchronously.")
        process_webhook_record(event.id)

    return WebhookIngestResponse(
        event_id=event_id,
        status="RECEIVED",
        message=f"Webhook event accepted and queued for asynchronous processing.",
        idempotent_duplicate=False,
    )


def process_webhook_record(event_id: uuid.UUID) -> Dict[str, Any]:
    """
    Synchronous processing engine for Celery background workers.
    Parses event payload, normalizes to FHIR R4, updates clinical tables, and updates event status.
    """
    logger.info(f"Processing webhook record: {event_id}")
    with get_sync_db() as db:
        event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
        if not event:
            return {"success": False, "error": f"WebhookEvent {event_id} not found."}

        event.status = WebhookStatus.PROCESSING
        db.commit()

        try:
            payload = event.payload
            event_type = event.event_type.lower()
            detected_type = detect_resource_type(payload)

            # Route by event type or auto-detected clinical payload
            if "patient" in event_type or detected_type == "Patient":
                normalized, _ = normalize_patient(payload)
                mrn_val = str(normalized.get("id") or payload.get("vendor_patient_id") or "WEBHOOK-MRN")
                patient = db.query(Patient).filter(Patient.mrn == mrn_val).first()
                if not patient:
                    name_data = normalized.get("name", [{}])[0]
                    patient = Patient(
                        mrn=mrn_val,
                        first_name=name_data.get("given", ["Unknown"])[0] if name_data.get("given") else "Unknown",
                        last_name=name_data.get("family", "Unknown"),
                        gender=normalized.get("gender", "unknown"),
                        is_active=True,
                    )
                    db.add(patient)
                    db.flush()

            elif "observation" in event_type or "vitals" in event_type or detected_type == "Observation":
                normalized, _ = normalize_observation(payload)
                first_p = db.query(Patient).first()
                if first_p:
                    checksum = compute_payload_checksum(payload)
                    rec = PatientRecord(
                        patient_id=first_p.id,
                        integration_id=event.integration_id,
                        resource_type="Observation",
                        fhir_version="R4",
                        status="final",
                        checksum=checksum,
                        raw_payload=payload,
                        normalized_payload=normalized,
                    )
                    db.add(rec)
                    db.flush()

            elif "condition" in event_type or detected_type == "Condition":
                normalized, _ = normalize_condition(payload)
                first_p = db.query(Patient).first()
                if first_p:
                    checksum = compute_payload_checksum(payload)
                    rec = PatientRecord(
                        patient_id=first_p.id,
                        integration_id=event.integration_id,
                        resource_type="Condition",
                        fhir_version="R4",
                        status="active",
                        checksum=checksum,
                        raw_payload=payload,
                        normalized_payload=normalized,
                    )
                    db.add(rec)
                    db.flush()

            event.status = WebhookStatus.PROCESSED
            event.processed_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"WebhookEvent {event_id} processed successfully.")
            return {"success": True, "event_id": str(event_id)}

        except Exception as exc:
            logger.error(f"Failed processing webhook event {event_id}: {exc}")
            event.status = WebhookStatus.FAILED
            event.error_message = str(exc)
            event.retry_count += 1
            db.commit()
            return {"success": False, "error": str(exc), "event_id": str(event_id)}


async def list_webhook_events(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
    source: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> WebhookEventListResponse:
    """Retrieves paginated webhook event log history with source and status filters."""
    query = select(WebhookEvent)
    if source:
        query = query.where(WebhookEvent.source == source.strip())
    if status_filter:
        query = query.where(WebhookEvent.status == status_filter.upper().strip())

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_q)
    total = count_res.scalar_one()

    # Paginate
    paged_q = query.order_by(WebhookEvent.created_at.desc()).offset((page - 1) * size).limit(size)
    res = await db.execute(paged_q)
    events = res.scalars().all()

    items = [WebhookEventResponse.model_validate(e) for e in events]
    return WebhookEventListResponse(items=items, total=total, page=page, size=size)


async def retry_webhook_event(db: AsyncSession, event_id: uuid.UUID) -> WebhookEventResponse:
    """Resets error state and re-enqueues a failed webhook event for asynchronous execution."""
    event = await db.get(WebhookEvent, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook event with ID {event_id} not found.",
        )

    event.status = WebhookStatus.RECEIVED
    event.error_message = None
    await db.commit()
    await db.refresh(event)

    try:
        from app.tasks.webhook_tasks import process_webhook_event_task
        process_webhook_event_task.delay(str(event.id))
    except Exception:
        process_webhook_record(event.id)

    return WebhookEventResponse.model_validate(event)
