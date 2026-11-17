from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    require_any_authenticated,
    require_analyst,
    require_admin,
)
from app.database import get_db
from app.models.user import User
from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientListResponse,
    PatientRecordCreate,
    PatientRecordResponse,
)
from app.services import patient_service

router = APIRouter()


@router.get(
    "",
    response_model=PatientListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Patient Demographics",
    description="Retrieves a paginated list of patient profiles with optional full-text search across MRN, first name, and last name.",
)
async def get_patients(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for MRN, First Name, or Last Name"),
    gender: Optional[str] = Query(None, description="Filter by gender (male, female, other, unknown)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
):
    return await patient_service.list_patients(
        db=db,
        page=page,
        size=size,
        search=search,
        gender=gender,
        is_active=is_active,
    )


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Patient Profile",
    description="Registers a new patient with a globally unique Medical Record Number (MRN). Requires CLINICAL_ANALYST or ADMIN role.",
)
async def create_new_patient(
    request: Request,
    patient_in: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    patient = await patient_service.create_patient(
        db=db,
        patient_in=patient_in,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    return patient


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Patient by ID",
    description="Retrieves full demographic profile for a specific patient UUID and logs clinical data access.",
)
async def get_patient_details(
    request: Request,
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await patient_service.get_patient_by_id(
        db=db,
        patient_id=patient_id,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Patient Demographics",
    description="Applies partial updates to patient demographic records. Requires CLINICAL_ANALYST or ADMIN role.",
)
async def update_patient_details(
    request: Request,
    patient_id: uuid.UUID,
    patient_in: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await patient_service.update_patient(
        db=db,
        patient_id=patient_id,
        patient_in=patient_in,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Patient Record",
    description="Permanently deletes a patient profile and associated clinical records. Strictly restricted to ADMIN role.",
)
async def delete_patient_record(
    request: Request,
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await patient_service.delete_patient(
        db=db,
        patient_id=patient_id,
        current_user=current_user,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    return None


@router.get(
    "/{patient_id}/records",
    response_model=List[PatientRecordResponse],
    status_code=status.HTTP_200_OK,
    summary="List Patient Clinical FHIR Records",
    description="Retrieves all normalized FHIR resources (Observations, Conditions, Encounters) linked to this patient.",
)
async def get_patient_clinical_records(
    patient_id: uuid.UUID,
    resource_type: Optional[str] = Query(None, description="Filter by FHIR resourceType (e.g. Observation, Condition)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
):
    return await patient_service.list_patient_records(
        db=db,
        patient_id=patient_id,
        resource_type=resource_type,
    )


@router.post(
    "/{patient_id}/records",
    response_model=PatientRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Clinical Record to Patient",
    description="Stores a raw clinical payload alongside its normalized FHIR representation with cryptographic checksum.",
)
async def add_patient_clinical_record(
    patient_id: uuid.UUID,
    record_in: PatientRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    return await patient_service.create_patient_record(
        db=db,
        patient_id=patient_id,
        record_in=record_in,
        current_user=current_user,
    )
