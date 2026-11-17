from datetime import date
import uuid
import pytest
from pydantic import ValidationError

from app.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientRecordCreate,
)
from app.services.patient_service import compute_payload_checksum
from app.main import app


def test_payload_checksum_deterministic():
    """Verify that payload checksum generation is deterministic regardless of key ordering."""
    payload_a = {"code": "85354-9", "systolic": 120, "diastolic": 80}
    payload_b = {"diastolic": 80, "systolic": 120, "code": "85354-9"}
    checksum_a = compute_payload_checksum(payload_a)
    checksum_b = compute_payload_checksum(payload_b)
    assert checksum_a == checksum_b
    assert len(checksum_a) == 64 # SHA-256 hex string


def test_patient_create_schema_validation():
    """Verify PatientCreate constraints and validation."""
    # Fails if MRN too short (< 3 chars)
    with pytest.raises(ValidationError):
        PatientCreate(
            mrn="M",
            first_name="Jane",
            last_name="Doe",
        )

    # Valid patient model
    valid_p = PatientCreate(
        mrn="MRN-TEST-001",
        first_name="Alice",
        last_name="Johnson",
        birth_date=date(1990, 5, 20),
        gender="female",
    )
    assert valid_p.mrn == "MRN-TEST-001"
    assert valid_p.gender == "female"
    assert valid_p.is_active is True


def test_patient_update_schema_partial():
    """Verify PatientUpdate permits partial field updates."""
    update = PatientUpdate(first_name="Alicia")
    dump = update.model_dump(exclude_unset=True)
    assert dump == {"first_name": "Alicia"}
    assert "last_name" not in dump


def test_patient_record_create_schema():
    """Verify PatientRecordCreate schema requires raw payload and resource type."""
    raw = {"test": "glucose", "value": 110}
    record = PatientRecordCreate(
        resource_type="Observation",
        raw_payload=raw,
        status="final"
    )
    assert record.resource_type == "Observation"
    assert record.fhir_version == "R4"
    assert record.raw_payload == raw


def test_patient_openapi_routes_registered():
    """Verify that all required Patient and FHIR endpoints are mapped in OpenAPI schema."""
    paths = app.openapi()["paths"]
    # API v1 routes
    assert "/api/v1/patients" in paths
    assert "get" in paths["/api/v1/patients"]
    assert "post" in paths["/api/v1/patients"]

    assert "/api/v1/patients/{patient_id}" in paths
    assert "get" in paths["/api/v1/patients/{patient_id}"]
    assert "put" in paths["/api/v1/patients/{patient_id}"]
    assert "delete" in paths["/api/v1/patients/{patient_id}"]

    assert "/api/v1/patients/{patient_id}/records" in paths
    assert "get" in paths["/api/v1/patients/{patient_id}/records"]
    assert "post" in paths["/api/v1/patients/{patient_id}/records"]

    # Root alias routes (required by Section 5)
    assert "/patients" in paths
    assert "/patients/{patient_id}" in paths
