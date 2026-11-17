import logging
from typing import Dict, Any, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.validation import ValidationErrorLog, ValidationSeverity, ValidationErrorType
from app.schemas.normalization import (
    NormalizeResponse,
    ValidateResponse,
    ValidationIssue,
)
from app.services.patient_service import compute_payload_checksum
from app.services.normalization.normalizer import (
    detect_resource_type,
    normalize_patient,
    normalize_observation,
    normalize_condition,
    validate_fhir_payload,
)

logger = logging.getLogger("medisync.normalization_service")


async def process_normalization(
    raw_payload: Dict[str, Any],
    source_type: str = "AUTO",
    resource_type: Optional[str] = None,
    db: Optional[AsyncSession] = None,
    sync_job_id: Optional[uuid.UUID] = None,
    patient_record_id: Optional[uuid.UUID] = None,
) -> NormalizeResponse:
    """
    Standardizes external healthcare JSON records into FHIR R4 format,
    computes idempotency checksums, and records validation anomalies.
    """
    detected_type = resource_type or detect_resource_type(raw_payload)

    if detected_type == "Patient":
        normalized, issues = normalize_patient(raw_payload)
    elif detected_type == "Observation":
        normalized, issues = normalize_observation(raw_payload)
    elif detected_type == "Condition":
        normalized, issues = normalize_condition(raw_payload)
    else:
        # Fallback raw preservation
        normalized = raw_payload.copy()
        issues = [
            ValidationIssue(
                field_path="resourceType",
                error_type=ValidationErrorType.INVALID_FHIR,
                severity=ValidationSeverity.WARNING,
                message=f"Unable to auto-classify payload into FHIR resourceType. Stored in raw form.",
            )
        ]

    checksum = compute_payload_checksum(raw_payload)
    is_valid = not any(i.severity == ValidationSeverity.CRITICAL for i in issues)

    # Persist validation errors into database if session is provided
    if db and issues:
        for issue in issues:
            log_entry = ValidationErrorLog(
                record_id=patient_record_id,
                sync_job_id=sync_job_id,
                resource_type=detected_type,
                field_path=issue.field_path,
                error_type=issue.error_type,
                severity=issue.severity,
                error_message=issue.message,
                raw_value={"input": issue.raw_value} if issue.raw_value is not None else None,
            )
            db.add(log_entry)
        await db.commit()

    return NormalizeResponse(
        success=True,
        resource_type=detected_type,
        checksum=checksum,
        normalized_payload=normalized,
        raw_payload=raw_payload,
        is_valid_fhir=is_valid,
        issues=issues,
    )


def validate_payload(resource_type: str, payload: Dict[str, Any]) -> ValidateResponse:
    """Validates candidate JSON against strict FHIR R4 specifications."""
    is_valid, issues = validate_fhir_payload(resource_type, payload)
    return ValidateResponse(
        is_valid=is_valid,
        resource_type=resource_type,
        issues=issues,
    )


async def list_validation_errors(
    db: AsyncSession,
    limit: int = 50,
    severity: Optional[str] = None,
) -> List[ValidationErrorLog]:
    """Retrieves recent clinical and structural validation errors from the database."""
    query = select(ValidationErrorLog)
    if severity:
        query = query.where(ValidationErrorLog.severity == severity.upper())

    query = query.order_by(ValidationErrorLog.created_at.desc()).limit(limit)
    res = await db.execute(query)
    return list(res.scalars().all())
