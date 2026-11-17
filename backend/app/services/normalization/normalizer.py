from datetime import datetime, date
import re
from typing import Dict, Any, List, Tuple, Optional
from pydantic import ValidationError

from app.models.validation import ValidationErrorType, ValidationSeverity
from app.schemas.normalization import ValidationIssue
from app.schemas.fhir import (
    FHIRPatientResource,
    FHIRObservationResource,
    FHIRConditionResource,
    FHIRIdentifier,
    FHIRHumanName,
    FHIRCodeableConcept,
    FHIRCoding,
    FHIRQuantity,
)


def detect_resource_type(raw_payload: Dict[str, Any]) -> str:
    """Intelligently detects whether a payload represents a Patient, Observation, or Condition."""
    if "resourceType" in raw_payload:
        return raw_payload["resourceType"]

    keys = set(k.lower() for k in raw_payload.keys())

    # Patient indicators
    if any(k in keys for k in ["patient_name", "first_name", "dob_string", "birth_date", "gender_code", "mrn", "vendor_patient_id"]):
        return "Patient"

    # Observation indicators
    if any(k in keys for k in ["bp", "systolic", "diastolic", "blood_sugar", "bpm", "heart_rate", "vitals", "vitals_summary", "test"]):
        return "Observation"

    # Condition indicators
    if any(k in keys for k in ["diagnosis", "icd10", "condition", "clinical_status", "problem"]):
        return "Condition"

    return "Unknown"


def parse_name(name_str: Optional[str]) -> Tuple[Optional[str], List[str]]:
    """Splits vendor names formatted as 'Last, First' or 'First Last' into family and given components."""
    if not name_str:
        return None, []

    clean = name_str.strip()
    if "," in clean:
        parts = [p.strip() for p in clean.split(",", 1)]
        family = parts[0]
        given = [p for p in parts[1].split() if p]
        return family, given
    else:
        parts = clean.split()
        if len(parts) == 1:
            return parts[0], []
        return parts[-1], parts[:-1]


def normalize_date(date_val: Optional[Any]) -> Optional[str]:
    """Converts diverse date strings (YYYY/MM/DD, MM/DD/YYYY, YYYY-MM-DD) into standard ISO YYYY-MM-DD."""
    if not date_val:
        return None
    if isinstance(date_val, (date, datetime)):
        return date_val.strftime("%Y-%m-%d")

    s = str(date_val).strip()
    # YYYY/MM/DD or YYYY-MM-DD
    m1 = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$", s)
    if m1:
        year, month, day = m1.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    # MM/DD/YYYY or MM-DD-YYYY
    m2 = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", s)
    if m2:
        month, day, year = m2.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    return s


def normalize_gender(gender_val: Optional[Any]) -> str:
    """Standardizes disparate gender inputs into FHIR AdministrativeGender: male, female, other, unknown."""
    if not gender_val:
        return "unknown"
    g = str(gender_val).strip().lower()
    if g in ["m", "male", "man"]:
        return "male"
    elif g in ["f", "female", "woman"]:
        return "female"
    elif g in ["o", "other", "non-binary"]:
        return "other"
    return "unknown"


# 1. Patient Normalization
def normalize_patient(raw_payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[ValidationIssue]]:
    """Normalizes vendor demographic JSON into a compliant FHIR R4 Patient resource."""
    issues: List[ValidationIssue] = []

    # If already standard FHIR, validate and return
    if raw_payload.get("resourceType") == "Patient":
        is_valid, validation_issues = validate_fhir_payload("Patient", raw_payload)
        return raw_payload, validation_issues

    # Extract ID and MRN
    patient_id = raw_payload.get("vendor_patient_id") or raw_payload.get("mrn") or raw_payload.get("id")
    if not patient_id:
        issues.append(
            ValidationIssue(
                field_path="identifier",
                error_type=ValidationErrorType.MISSING_FIELD,
                severity=ValidationSeverity.WARNING,
                message="Patient record lacks a primary MRN or vendor identifier.",
            )
        )
        patient_id = "UNKNOWN-ID"

    # Name extraction
    family = None
    given: List[str] = []
    if "patient_name" in raw_payload:
        family, given = parse_name(raw_payload["patient_name"])
    else:
        family = raw_payload.get("last_name") or raw_payload.get("family")
        g = raw_payload.get("first_name") or raw_payload.get("given")
        if g:
            given = [g] if isinstance(g, str) else list(g)

    if not family and not given:
        issues.append(
            ValidationIssue(
                field_path="name",
                error_type=ValidationErrorType.MISSING_FIELD,
                severity=ValidationSeverity.WARNING,
                message="Patient name fields (first/last) are missing.",
            )
        )

    # Birth date normalization
    raw_dob = raw_payload.get("dob_string") or raw_payload.get("birth_date") or raw_payload.get("birthDate")
    normalized_dob = normalize_date(raw_dob)
    if not normalized_dob:
        issues.append(
            ValidationIssue(
                field_path="birthDate",
                error_type=ValidationErrorType.MISSING_FIELD,
                severity=ValidationSeverity.INFO,
                message="Birth date is missing from source payload.",
            )
        )

    # Gender normalization
    raw_gender = raw_payload.get("gender_code") or raw_payload.get("gender")
    normalized_gender = normalize_gender(raw_gender)

    # Assemble FHIR Patient Resource
    fhir_patient: Dict[str, Any] = {
        "resourceType": "Patient",
        "id": str(patient_id),
        "identifier": [
            {
                "system": "http://medisync.local/mrn",
                "value": str(patient_id),
                "use": "usual",
            }
        ],
        "active": raw_payload.get("active", True),
        "name": [
            {
                "use": "official",
                "family": family,
                "given": given,
                "text": f"{' '.join(given)} {family}".strip() if family or given else None,
            }
        ],
        "gender": normalized_gender,
        "birthDate": normalized_dob,
    }

    # Telecom / Address if present
    phone = raw_payload.get("phone_number") or raw_payload.get("phone")
    if phone:
        fhir_patient["telecom"] = [{"system": "phone", "value": str(phone)}]

    # Validate against Pydantic schema
    _, schema_issues = validate_fhir_payload("Patient", fhir_patient)
    issues.extend(schema_issues)

    return fhir_patient, issues


# 2. Observation Normalization
def normalize_observation(raw_payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[ValidationIssue]]:
    """Normalizes vital signs or lab results into a compliant FHIR R4 Observation resource."""
    issues: List[ValidationIssue] = []

    if raw_payload.get("resourceType") == "Observation":
        _, validation_issues = validate_fhir_payload("Observation", raw_payload)
        return raw_payload, validation_issues

    # Case A: Blood Pressure Panel
    bp_str = raw_payload.get("bp") or (raw_payload.get("vitals_summary", {}).get("bp") if isinstance(raw_payload.get("vitals_summary"), dict) else None)
    systolic = raw_payload.get("systolic")
    diastolic = raw_payload.get("diastolic")

    if bp_str and ("/" in str(bp_str)):
        parts = str(bp_str).split("/")
        try:
            systolic = float(parts[0].strip())
            diastolic = float(parts[1].strip())
        except ValueError:
            issues.append(
                ValidationIssue(
                    field_path="component.valueQuantity",
                    error_type=ValidationErrorType.TYPE_MISMATCH,
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Could not parse numeric blood pressure from '{bp_str}'",
                    raw_value=bp_str,
                )
            )

    if systolic is not None or diastolic is not None:
        # Clinical Range Checks
        if systolic and (systolic > 240 or systolic < 50):
            issues.append(
                ValidationIssue(
                    field_path="component[0].valueQuantity.value",
                    error_type=ValidationErrorType.BUSINESS_RULE_VIOLATION,
                    severity=ValidationSeverity.WARNING,
                    message=f"Systolic blood pressure {systolic} mmHg is outside standard physiological range (50-240).",
                    raw_value=systolic,
                )
            )
        if diastolic and (diastolic > 150 or diastolic < 30):
            issues.append(
                ValidationIssue(
                    field_path="component[1].valueQuantity.value",
                    error_type=ValidationErrorType.BUSINESS_RULE_VIOLATION,
                    severity=ValidationSeverity.WARNING,
                    message=f"Diastolic blood pressure {diastolic} mmHg is outside standard physiological range (30-150).",
                    raw_value=diastolic,
                )
            )

        fhir_obs = {
            "resourceType": "Observation",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "85354-9",
                        "display": "Blood pressure panel with all children optional",
                    }
                ],
                "text": "Blood Pressure",
            },
            "component": [
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "8480-6",
                                "display": "Systolic blood pressure",
                            }
                        ]
                    },
                    "valueQuantity": {"value": float(systolic) if systolic else 0.0, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"},
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "8462-4",
                                "display": "Diastolic blood pressure",
                            }
                        ]
                    },
                    "valueQuantity": {"value": float(diastolic) if diastolic else 0.0, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"},
                },
            ],
        }
        _, schema_issues = validate_fhir_payload("Observation", fhir_obs)
        issues.extend(schema_issues)
        return fhir_obs, issues

    # Case B: Heart Rate / Pulse
    heart_rate = raw_payload.get("bpm") or raw_payload.get("heart_rate") or (raw_payload.get("vitals_summary", {}).get("heart_rate") if isinstance(raw_payload.get("vitals_summary"), dict) else None)
    if heart_rate is not None:
        try:
            hr_val = float(heart_rate)
        except ValueError:
            hr_val = 0.0

        fhir_obs = {
            "resourceType": "Observation",
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}],
                "text": "Heart Rate",
            },
            "valueQuantity": {
                "value": hr_val,
                "unit": "/min",
                "system": "http://unitsofmeasure.org",
                "code": "/min",
            },
        }
        _, schema_issues = validate_fhir_payload("Observation", fhir_obs)
        issues.extend(schema_issues)
        return fhir_obs, issues

    # Fallback generic observation
    fhir_obs = {
        "resourceType": "Observation",
        "status": "final",
        "code": {
            "coding": [{"system": "http://medisync.local/observation", "code": "GENERIC_OBS", "display": "Unclassified Clinical Observation"}],
            "text": str(raw_payload.get("metric") or raw_payload.get("test") or "Clinical Observation"),
        },
    }
    return fhir_obs, issues


# 3. Condition Normalization
def normalize_condition(raw_payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[ValidationIssue]]:
    """Normalizes diagnosis strings or ICD codes into a compliant FHIR R4 Condition resource."""
    issues: List[ValidationIssue] = []

    if raw_payload.get("resourceType") == "Condition":
        _, validation_issues = validate_fhir_payload("Condition", raw_payload)
        return raw_payload, validation_issues

    diagnosis = raw_payload.get("diagnosis") or raw_payload.get("condition") or "Unspecified Health Condition"
    icd10 = raw_payload.get("icd10") or raw_payload.get("code")

    coding_list: List[Dict[str, Any]] = []
    if icd10:
        coding_list.append({
            "system": "http://hl7.org/fhir/sid/icd-10",
            "code": str(icd10).strip(),
            "display": str(diagnosis),
        })
    else:
        coding_list.append({
            "system": "http://snomed.info/sct",
            "code": "UNKNOWN",
            "display": str(diagnosis),
        })
        issues.append(
            ValidationIssue(
                field_path="code.coding[0].code",
                error_type=ValidationErrorType.MISSING_FIELD,
                severity=ValidationSeverity.WARNING,
                message="Diagnosis lacks standard ICD-10 or SNOMED CT terminology code.",
            )
        )

    fhir_condition = {
        "resourceType": "Condition",
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": raw_payload.get("clinical_status", "active"),
                }
            ]
        },
        "code": {
            "coding": coding_list,
            "text": str(diagnosis),
        },
        "onsetDateTime": normalize_date(raw_payload.get("onset")),
    }

    _, schema_issues = validate_fhir_payload("Condition", fhir_condition)
    issues.extend(schema_issues)
    return fhir_condition, issues


# 4. FHIR R4 Schema Validator (Pydantic)
def validate_fhir_payload(resource_type: str, payload: Dict[str, Any]) -> Tuple[bool, List[ValidationIssue]]:
    """Validates candidate payloads against strict Pydantic FHIR R4 schemas."""
    issues: List[ValidationIssue] = []
    r_type = resource_type.capitalize().strip()

    try:
        if r_type == "Patient":
            FHIRPatientResource.model_validate(payload)
        elif r_type == "Observation":
            FHIRObservationResource.model_validate(payload)
        elif r_type == "Condition":
            FHIRConditionResource.model_validate(payload)
        else:
            issues.append(
                ValidationIssue(
                    field_path="resourceType",
                    error_type=ValidationErrorType.INVALID_FHIR,
                    severity=ValidationSeverity.WARNING,
                    message=f"Unsupported or unmapped FHIR resourceType: {resource_type}",
                )
            )
            return False, issues
        return True, []
    except ValidationError as err:
        for error in err.errors():
            loc = ".".join(str(x) for x in error["loc"])
            issues.append(
                ValidationIssue(
                    field_path=loc,
                    error_type=ValidationErrorType.INVALID_FHIR,
                    severity=ValidationSeverity.CRITICAL,
                    message=error["msg"],
                    raw_value=error.get("input"),
                )
            )
        return False, issues
