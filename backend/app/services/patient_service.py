import hashlib
import json
import logging
import math
from typing import List, Optional, Tuple
import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient, PatientRecord
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientRecordCreate,
    PatientListResponse,
    PatientResponse,
)

logger = logging.getLogger("medisync.patient_service")


def compute_payload_checksum(payload: dict) -> str:
    """Computes a deterministic SHA-256 checksum of a JSON payload for deduplication and audit."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


async def list_patients(
    db: AsyncSession,
    page: int = 1,
    size: int = 20,
    search: Optional[str] = None,
    gender: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> PatientListResponse:
    """Retrieves paginated patient demographics with dynamic search and filter support."""
    query = select(Patient)

    if search:
        search_filter = f"%{search.strip()}%"
        query = query.where(
            or_(
                Patient.mrn.ilike(search_filter),
                Patient.first_name.ilike(search_filter),
                Patient.last_name.ilike(search_filter),
            )
        )

    if gender:
        query = query.where(Patient.gender == gender.lower().strip())

    if is_active is not None:
        query = query.where(Patient.is_active == is_active)

    # 1. Total count
    count_query = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_query)
    total = count_res.scalar_one()

    # 2. Paginated results
    offset = (page - 1) * size
    paged_query = query.offset(offset).limit(size).order_by(Patient.created_at.desc())
    records_res = await db.execute(paged_query)
    patients = records_res.scalars().all()

    items = [PatientResponse.model_validate(p) for p in patients]
    pages = math.ceil(total / size) if size > 0 else 0

    return PatientListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


async def get_patient_by_id(
    db: AsyncSession,
    patient_id: uuid.UUID,
    current_user: Optional[User] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Patient:
    """Retrieves a single patient record by UUID and logs clinical data access."""
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} was not found.",
        )

    # HIPAA-compliant audit logging for clinical record access
    if current_user:
        audit_entry = AuditLog(
            user_id=current_user.id,
            action="PATIENT_READ",
            resource_type="Patient",
            resource_id=str(patient.id),
            ip_address=ip_address,
            user_agent=user_agent,
            details={"mrn": patient.mrn, "patient_name": f"{patient.first_name} {patient.last_name}"},
        )
        db.add(audit_entry)
        await db.commit()

    return patient


async def create_patient(
    db: AsyncSession,
    patient_in: PatientCreate,
    current_user: Optional[User] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Patient:
    """Creates a new patient profile, ensuring MRN uniqueness and writing an audit trail."""
    # Enforce MRN uniqueness
    existing_q = select(Patient).where(Patient.mrn == patient_in.mrn.strip())
    existing_res = await db.execute(existing_q)
    if existing_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient with MRN '{patient_in.mrn}' already exists in the system.",
        )

    patient = Patient(
        mrn=patient_in.mrn.strip(),
        first_name=patient_in.first_name.strip(),
        last_name=patient_in.last_name.strip(),
        birth_date=patient_in.birth_date,
        gender=patient_in.gender.lower().strip() if patient_in.gender else "unknown",
        contact_info=patient_in.contact_info,
        address=patient_in.address,
        is_active=patient_in.is_active,
    )
    db.add(patient)
    await db.flush()

    if current_user:
        audit_entry = AuditLog(
            user_id=current_user.id,
            action="PATIENT_CREATE",
            resource_type="Patient",
            resource_id=str(patient.id),
            ip_address=ip_address,
            user_agent=user_agent,
            details={"mrn": patient.mrn},
        )
        db.add(audit_entry)

    await db.commit()
    await db.refresh(patient)
    logger.info(f"Created patient {patient.mrn} ({patient.first_name} {patient.last_name})")
    return patient


async def update_patient(
    db: AsyncSession,
    patient_id: uuid.UUID,
    patient_in: PatientUpdate,
    current_user: Optional[User] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Patient:
    """Updates an existing patient record with partial modifications."""
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} was not found.",
        )

    update_data = patient_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(patient, field, val)

    if current_user:
        audit_entry = AuditLog(
            user_id=current_user.id,
            action="PATIENT_UPDATE",
            resource_type="Patient",
            resource_id=str(patient.id),
            ip_address=ip_address,
            user_agent=user_agent,
            details={"updated_fields": list(update_data.keys())},
        )
        db.add(audit_entry)

    await db.commit()
    await db.refresh(patient)
    logger.info(f"Updated patient {patient.id} ({list(update_data.keys())})")
    return patient


async def delete_patient(
    db: AsyncSession,
    patient_id: uuid.UUID,
    current_user: Optional[User] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Deletes a patient and their associated clinical records, leaving a permanent audit trail."""
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} was not found.",
        )

    patient_mrn = patient.mrn
    await db.delete(patient)

    if current_user:
        audit_entry = AuditLog(
            user_id=current_user.id,
            action="PATIENT_DELETE",
            resource_type="Patient",
            resource_id=str(patient_id),
            ip_address=ip_address,
            user_agent=user_agent,
            details={"deleted_mrn": patient_mrn},
        )
        db.add(audit_entry)

    await db.commit()
    logger.warning(f"Deleted patient {patient_id} (MRN: {patient_mrn}) by user {current_user.id if current_user else 'system'}")


async def create_patient_record(
    db: AsyncSession,
    patient_id: uuid.UUID,
    record_in: PatientRecordCreate,
    current_user: Optional[User] = None,
) -> PatientRecord:
    """Stores a raw vendor record alongside its standardized FHIR resource."""
    # Ensure patient exists
    patient = await db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot attach clinical record. Patient {patient_id} does not exist.",
        )

    checksum = compute_payload_checksum(record_in.raw_payload)
    normalized = record_in.normalized_payload or record_in.raw_payload

    record = PatientRecord(
        patient_id=patient_id,
        provider_id=record_in.provider_id,
        integration_id=record_in.integration_id,
        resource_type=record_in.resource_type,
        fhir_version=record_in.fhir_version,
        status=record_in.status,
        checksum=checksum,
        raw_payload=record_in.raw_payload,
        normalized_payload=normalized,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def list_patient_records(
    db: AsyncSession,
    patient_id: uuid.UUID,
    resource_type: Optional[str] = None,
) -> List[PatientRecord]:
    """Retrieves all clinical resources attached to a patient."""
    query = select(PatientRecord).where(PatientRecord.patient_id == patient_id)
    if resource_type:
        query = query.where(PatientRecord.resource_type == resource_type)

    query = query.order_by(PatientRecord.created_at.desc())
    res = await db.execute(query)
    return list(res.scalars().all())
