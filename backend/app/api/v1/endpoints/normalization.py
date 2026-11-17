from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_any_authenticated, require_engineer
from app.database import get_db
from app.models.user import User
from app.schemas.normalization import (
    NormalizeRequest,
    NormalizeResponse,
    ValidateRequest,
    ValidateResponse,
    ValidationErrorLogResponse,
)
from app.services import normalization_service

router = APIRouter()


@router.post(
    "/normalize",
    response_model=NormalizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Normalize Healthcare JSON to FHIR R4",
    description="Transforms non-standard vendor EHR payloads (names, dates, vitals, diagnostics) into standardized FHIR R4 resources with validation diagnostics.",
)
async def normalize_healthcare_record(
    payload_in: NormalizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
):
    return await normalization_service.process_normalization(
        raw_payload=payload_in.raw_payload,
        source_type=payload_in.source_type,
        resource_type=payload_in.resource_type,
        db=db,
    )


@router.post(
    "/validate",
    response_model=ValidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate FHIR Resource Schema",
    description="Validates candidate JSON payloads directly against strict Pydantic FHIR R4 resource definitions (Patient, Observation, Condition).",
)
def validate_fhir_resource(
    payload_in: ValidateRequest,
    current_user: User = Depends(require_any_authenticated),
):
    return normalization_service.validate_payload(
        resource_type=payload_in.resource_type,
        payload=payload_in.payload,
    )


@router.get(
    "/errors",
    response_model=List[ValidationErrorLogResponse],
    status_code=status.HTTP_200_OK,
    summary="List Clinical & Schema Validation Errors",
    description="Retrieves recent validation error logs and warnings detected during data ingestion.",
)
async def get_validation_errors(
    limit: int = Query(50, ge=1, le=200, description="Max errors to return"),
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, WARNING, INFO"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    return await normalization_service.list_validation_errors(
        db=db,
        limit=limit,
        severity=severity,
    )
