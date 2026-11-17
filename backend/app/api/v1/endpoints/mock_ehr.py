from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Query, status

router = APIRouter()

# Synthetic Mock FHIR R4 Repository
MOCK_PATIENTS = [
    {
        "fullUrl": "urn:uuid:6c9b3a32-15f1-4db8-9e22-87588b398601",
        "resource": {
            "resourceType": "Patient",
            "id": "6c9b3a32-15f1-4db8-9e22-87588b398601",
            "identifier": [{"system": "http://hospital.demo/mrn", "value": "MRN-MOCK-001"}],
            "active": True,
            "name": [{"family": "Williams", "given": ["Ethan"]}],
            "gender": "male",
            "birthDate": "1980-06-15",
            "telecom": [{"system": "phone", "value": "555-8891"}, {"system": "email", "value": "ethan.williams@example.com"}],
            "address": [{"line": ["100 Beacon St"], "city": "Boston", "state": "MA", "postalCode": "02116", "country": "USA"}]
        }
    },
    {
        "fullUrl": "urn:uuid:6c9b3a32-15f1-4db8-9e22-87588b398602",
        "resource": {
            "resourceType": "Patient",
            "id": "6c9b3a32-15f1-4db8-9e22-87588b398602",
            "identifier": [{"system": "http://hospital.demo/mrn", "value": "MRN-MOCK-002"}],
            "active": True,
            "name": [{"family": "Patel", "given": ["Priya"]}],
            "gender": "female",
            "birthDate": "1991-03-22",
            "telecom": [{"system": "phone", "value": "555-8892"}, {"system": "email", "value": "priya.patel@example.com"}],
            "address": [{"line": ["250 Main St"], "city": "Cambridge", "state": "MA", "postalCode": "02142", "country": "USA"}]
        }
    }
]

MOCK_OBSERVATIONS = [
    {
        "fullUrl": "urn:uuid:8a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
        "resource": {
            "resourceType": "Observation",
            "id": "8a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
            "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel with all children optional"}]},
            "subject": {"reference": "Patient/6c9b3a32-15f1-4db8-9e22-87588b398601"},
            "effectiveDateTime": "2026-11-01T09:30:00Z",
            "component": [
                {"code": {"coding": [{"code": "8480-6", "display": "Systolic blood pressure"}]}, "valueQuantity": {"value": 122, "unit": "mmHg"}},
                {"code": {"coding": [{"code": "8462-4", "display": "Diastolic blood pressure"}]}, "valueQuantity": {"value": 78, "unit": "mmHg"}}
            ]
        }
    }
]

MOCK_CONDITIONS = [
    {
        "fullUrl": "urn:uuid:9b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e",
        "resource": {
            "resourceType": "Condition",
            "id": "9b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e",
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "38341003", "display": "Hypertensive disorder"}]},
            "subject": {"reference": "Patient/6c9b3a32-15f1-4db8-9e22-87588b398601"},
            "onsetDateTime": "2023-01-10"
        }
    }
]


@router.get(
    "/mock-fhir/metadata",
    summary="Mock FHIR CapabilityStatement",
    description="Returns FHIR conformance metadata for connection diagnostic checks.",
    status_code=status.HTTP_200_OK
)
def get_fhir_metadata() -> Dict[str, Any]:
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": datetime.now(timezone.utc).isoformat(),
        "publisher": "MediSync AI Mock FHIR Gateway",
        "kind": "instance",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [{
            "mode": "server",
            "resource": [
                {"type": "Patient", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                {"type": "Observation", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                {"type": "Condition", "interaction": [{"code": "read"}, {"code": "search-type"}]}
            ]
        }]
    }


@router.get(
    "/mock-fhir/Patient",
    summary="Mock FHIR Patient Search",
    description="Returns FHIR R4 Bundle of Patient resources with pagination.",
    status_code=status.HTTP_200_OK
)
def get_mock_fhir_patients(
    _count: int = Query(10, description="Page limit"),
    _offset: int = Query(0, description="Offset")
) -> Dict[str, Any]:
    entries = MOCK_PATIENTS[_offset:_offset + _count]
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(MOCK_PATIENTS),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry": entries
    }


@router.get(
    "/mock-fhir/Observation",
    summary="Mock FHIR Observation Search",
    description="Returns FHIR R4 Bundle of Observation vitals resources.",
    status_code=status.HTTP_200_OK
)
def get_mock_fhir_observations(
    patient: Optional[str] = Query(None, description="Patient reference filter")
) -> Dict[str, Any]:
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(MOCK_OBSERVATIONS),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry": MOCK_OBSERVATIONS
    }


@router.get(
    "/mock-fhir/Condition",
    summary="Mock FHIR Condition Search",
    description="Returns FHIR R4 Bundle of Condition resources.",
    status_code=status.HTTP_200_OK
)
def get_mock_fhir_conditions() -> Dict[str, Any]:
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(MOCK_CONDITIONS),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry": MOCK_CONDITIONS
    }


@router.get(
    "/mock-vendor/records",
    summary="Mock Legacy Non-Standard EHR JSON",
    description="Returns vendor-specific EHR records with un-normalized clinical representations.",
    status_code=status.HTTP_200_OK
)
def get_mock_vendor_records() -> Dict[str, Any]:
    return {
        "hospital_code": "MEMORIAL-WEST",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "patients": [
            {
                "vendor_patient_id": "VEND-9901",
                "patient_name": "Jackson, Arthur",
                "dob_string": "1968/12/04",
                "gender_code": "M",
                "phone_number": "555-7721",
                "clinical_notes": [
                    {"note_type": "Progress Note", "body": "Patient reports mild dizziness in morning."}
                ],
                "vitals_summary": {
                    "bp": "135/88",
                    "heart_rate": 76,
                    "blood_sugar": 105
                }
            }
        ]
    }
