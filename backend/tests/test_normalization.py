import pytest

from app.services.normalization.normalizer import (
    detect_resource_type,
    normalize_patient,
    normalize_observation,
    normalize_condition,
    validate_fhir_payload,
)
from app.main import app


def test_resource_type_detection():
    """Verify auto-detection of clinical resource categories."""
    assert detect_resource_type({"patient_name": "Doe, Jane", "dob_string": "1990/01/01"}) == "Patient"
    assert detect_resource_type({"bp": "120/80", "heart_rate": 70}) == "Observation"
    assert detect_resource_type({"diagnosis": "Type 2 Diabetes", "icd10": "E11"}) == "Condition"
    assert detect_resource_type({"resourceType": "Observation", "code": {}}) == "Observation"


def test_patient_normalization_from_legacy_vendor():
    """Verify conversion of legacy non-standard patient JSON to standard FHIR R4."""
    legacy_vendor_payload = {
        "vendor_patient_id": "VEND-9901",
        "patient_name": "Jackson, Arthur",
        "dob_string": "1968/12/04",
        "gender_code": "M",
        "phone_number": "555-7721",
    }
    fhir_patient, issues = normalize_patient(legacy_vendor_payload)

    assert fhir_patient["resourceType"] == "Patient"
    assert fhir_patient["id"] == "VEND-9901"
    assert fhir_patient["gender"] == "male"
    assert fhir_patient["birthDate"] == "1968-12-04"
    assert fhir_patient["name"][0]["family"] == "Jackson"
    assert fhir_patient["name"][0]["given"] == ["Arthur"]
    assert fhir_patient["telecom"][0]["value"] == "555-7721"
    # No critical schema errors
    assert not any(i.severity.value == "CRITICAL" for i in issues)


def test_observation_normalization_blood_pressure():
    """Verify blood pressure parsing into LOINC components."""
    vendor_bp = {"bp": "135/88"}
    fhir_obs, issues = normalize_observation(vendor_bp)

    assert fhir_obs["resourceType"] == "Observation"
    assert fhir_obs["status"] == "final"
    assert fhir_obs["code"]["coding"][0]["code"] == "85354-9" # LOINC BP panel
    assert len(fhir_obs["component"]) == 2

    systolic_comp = fhir_obs["component"][0]
    diastolic_comp = fhir_obs["component"][1]
    assert systolic_comp["valueQuantity"]["value"] == 135.0
    assert diastolic_comp["valueQuantity"]["value"] == 88.0


def test_fhir_validator_catches_invalid_gender_and_status():
    """Verify Pydantic FHIR validator flags non-compliant values."""
    # Invalid administrative gender
    bad_patient = {
        "resourceType": "Patient",
        "gender": "alien",
    }
    is_valid, issues = validate_fhir_payload("Patient", bad_patient)
    assert is_valid is False
    assert any("gender" in i.field_path for i in issues)

    # Invalid observation status
    bad_obs = {
        "resourceType": "Observation",
        "status": "not-a-valid-status",
        "code": {"coding": [{"code": "1234"}]},
    }
    is_valid_obs, obs_issues = validate_fhir_payload("Observation", bad_obs)
    assert is_valid_obs is False


def test_normalization_openapi_routes_registered():
    """Verify that normalization endpoints are mapped in OpenAPI schema."""
    paths = app.openapi()["paths"]
    assert "/api/v1/normalization/normalize" in paths
    assert "/api/v1/normalization/validate" in paths
    assert "/api/v1/normalization/errors" in paths
    assert "/normalization/normalize" in paths
