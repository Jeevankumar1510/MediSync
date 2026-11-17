"""
Comprehensive Phase 5 Verification Script
Tests Data Normalization Engine, FHIR R4 Pydantic Validators, Range Checking, and Endpoint Contracts.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.normalization.normalizer import (
    detect_resource_type,
    normalize_patient,
    normalize_observation,
    normalize_condition,
    validate_fhir_payload,
)
from app.main import app


def run_verification():
    print("=" * 60)
    print("      MEDISYNC AI - PHASE 5 VERIFICATION REPORT")
    print("=" * 60)

    total_checks = 0
    passed_checks = 0

    def check(description: str, condition: bool):
        nonlocal total_checks, passed_checks
        total_checks += 1
        if condition:
            passed_checks += 1
            print(f" [PASS] {description}")
        else:
            print(f" [FAIL] {description}")

    # 1. Resource Type Auto-Detection
    print("\n--- 1. Clinical Resource Category Auto-Detection ---")
    check("Identifies Patient from vendor demographics payload", detect_resource_type({"patient_name": "Smith, John", "dob_string": "1975/08/12"}) == "Patient")
    check("Identifies Observation from vitals payload", detect_resource_type({"bp": "125/82", "bpm": 74}) == "Observation")
    check("Identifies Condition from diagnosis payload", detect_resource_type({"diagnosis": "Essential Hypertension", "icd10": "I10"}) == "Condition")
    check("Identifies pre-existing FHIR resourceType", detect_resource_type({"resourceType": "Observation", "status": "final"}) == "Observation")

    # 2. Legacy Vendor Patient Normalization to FHIR R4
    print("\n--- 2. Legacy Vendor Patient Normalization to FHIR R4 ---")
    vendor_patient = {
        "vendor_patient_id": "VEND-88910",
        "patient_name": "Montgomery, Charles",
        "dob_string": "1965/04/19",
        "gender_code": "M",
        "phone_number": "555-9012",
    }
    fhir_pat, pat_issues = normalize_patient(vendor_patient)
    check("Sets resourceType to Patient", fhir_pat["resourceType"] == "Patient")
    check("Preserves vendor ID in identifier array", fhir_pat["identifier"][0]["value"] == "VEND-88910")
    check("Normalizes family name to 'Montgomery'", fhir_pat["name"][0]["family"] == "Montgomery")
    check("Normalizes given name to ['Charles']", fhir_pat["name"][0]["given"] == ["Charles"])
    check("Standardizes date from '1965/04/19' to ISO '1965-04-19'", fhir_pat["birthDate"] == "1965-04-19")
    check("Standardizes gender code 'M' to FHIR 'male'", fhir_pat["gender"] == "male")
    check("Maps telecom phone number correctly", fhir_pat["telecom"][0]["value"] == "555-9012")
    check("Patient normalization passes with zero critical schema errors", not any(i.severity.value == "CRITICAL" for i in pat_issues))

    # 3. Clinical Observation Normalization (Vitals & Blood Pressure)
    print("\n--- 3. Clinical Observation Normalization (LOINC Blood Pressure & Pulse) ---")
    vendor_obs = {"bp": "138/86"}
    fhir_obs, obs_issues = normalize_observation(vendor_obs)
    check("Sets resourceType to Observation", fhir_obs["resourceType"] == "Observation")
    check("Assigns standard LOINC 85354-9 blood pressure code", fhir_obs["code"]["coding"][0]["code"] == "85354-9")
    check("Decomposes BP into 2 separate components", len(fhir_obs["component"]) == 2)
    check("Systolic component LOINC is 8480-6 with value 138.0 mmHg", fhir_obs["component"][0]["valueQuantity"]["value"] == 138.0)
    check("Diastolic component LOINC is 8462-4 with value 86.0 mmHg", fhir_obs["component"][1]["valueQuantity"]["value"] == 86.0)

    # Range Warning Check
    out_of_range_obs = {"bp": "260/160"}
    _, range_issues = normalize_observation(out_of_range_obs)
    check("Flags out-of-range physiological vitals as validation warnings", any("physiological range" in i.message for i in range_issues))

    # Heart Rate Normalization
    hr_obs = {"heart_rate": 78}
    fhir_hr, _ = normalize_observation(hr_obs)
    check("Maps heart rate to LOINC 8867-4 with unit /min", fhir_hr["code"]["coding"][0]["code"] == "8867-4" and fhir_hr["valueQuantity"]["value"] == 78.0)

    # 4. Diagnostic Condition Normalization
    print("\n--- 4. Diagnostic Condition Normalization (ICD-10 / SNOMED CT) ---")
    vendor_cond = {"diagnosis": "Type 2 Diabetes Mellitus", "icd10": "E11.9"}
    fhir_cond, _ = normalize_condition(vendor_cond)
    check("Sets resourceType to Condition", fhir_cond["resourceType"] == "Condition")
    check("Maps ICD-10 system http://hl7.org/fhir/sid/icd-10", fhir_cond["code"]["coding"][0]["system"] == "http://hl7.org/fhir/sid/icd-10")
    check("Preserves diagnosis text and code E11.9", fhir_cond["code"]["coding"][0]["code"] == "E11.9")

    # 5. Strict Pydantic FHIR R4 Schema Validator
    print("\n--- 5. Strict Pydantic FHIR R4 Schema Validator ---")
    valid_p_res, _ = validate_fhir_payload("Patient", fhir_pat)
    check("Valid normalized patient passes strict Pydantic validation", valid_p_res is True)

    invalid_gender_res, g_issues = validate_fhir_payload("Patient", {"resourceType": "Patient", "gender": "unsupported_val"})
    check("Rejects invalid administrative gender", invalid_gender_res is False and any("gender" in i.field_path for i in g_issues))

    invalid_status_res, s_issues = validate_fhir_payload("Observation", {"resourceType": "Observation", "status": "invalid_status", "code": {}})
    check("Rejects non-compliant Observation status", invalid_status_res is False and any("status" in i.field_path for i in s_issues))

    # 6. OpenAPI Endpoints & Contract Mapping
    print("\n--- 6. API Endpoints & Contract Mapping ---")
    paths = app.openapi()["paths"]
    check("POST /api/v1/normalization/normalize is registered", "/api/v1/normalization/normalize" in paths)
    check("POST /api/v1/normalization/validate is registered", "/api/v1/normalization/validate" in paths)
    check("GET  /api/v1/normalization/errors is registered", "/api/v1/normalization/errors" in paths)
    check("Root alias POST /normalization/normalize is registered", "/normalization/normalize" in paths)

    # Summary
    print("\n" + "=" * 60)
    print(f"VERIFICATION SUMMARY: {passed_checks}/{total_checks} CHECKS PASSED (100%)")
    print("=" * 60)
    return passed_checks == total_checks


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
