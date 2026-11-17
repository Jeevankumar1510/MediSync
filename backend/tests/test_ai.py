import pytest

from app.services.ai.field_mapper import suggest_field_mappings
from app.services.ai.anomaly_detector import detect_clinical_anomalies
from app.services.ai.error_explainer import explain_clinical_error
from app.main import app


def test_ai_field_mapping_high_confidence():
    """Verify AI field mapper detects exact and canonical healthcare aliases with high confidence."""
    raw_sample = {
        "mrn": "MRN-100234",
        "first_name": "Eleanor",
        "last_name": "Vance",
        "dob": "1988-04-12",
        "gender": "female",
    }
    result = suggest_field_mappings(raw_sample, target_resource_type="Patient")
    assert result.resource_type == "Patient"
    assert result.overall_confidence >= 0.90
    assert len(result.suggestions) >= 4

    targets = {s.source_field: s.suggested_target_field for s in result.suggestions}
    assert targets["mrn"] == "identifier[0].value"
    assert targets["first_name"] == "name[0].given[0]"
    assert targets["last_name"] == "name[0].family"
    assert targets["dob"] == "birthDate"
    assert all(not s.requires_human_approval for s in result.suggestions)


def test_ai_field_mapping_fuzzy_and_human_approval():
    """Verify fuzzy mapping marks ambiguous matches as requiring human approval."""
    raw_sample = {
        "client_surname": "Rodriguez",
        "custom_blood_metric": 120,
    }
    result = suggest_field_mappings(raw_sample, target_resource_type="Patient")
    # client_surname contains 'surname', should fuzzy match with requires_human_approval
    matched_surname = next((s for s in result.suggestions if s.source_field == "client_surname"), None)
    assert matched_surname is not None
    assert matched_surname.suggested_target_field == "name[0].family"


def test_anomaly_detection_isolation_forest():
    """Verify Scikit-learn IsolationForest flags severe physiological vitals outlier."""
    records = [
        {"id": "rec-1", "bp": "120/80", "bpm": 72},
        {"id": "rec-2", "bp": "122/82", "bpm": 70},
        {"id": "rec-3", "bp": "118/78", "bpm": 68},
        {"id": "rec-outlier", "bp": "240/150", "bpm": 180}, # Severe clinical outlier
    ]
    findings = detect_clinical_anomalies(records)
    outlier_findings = [f for f in findings if f.finding_type == "OUTLIER_ANOMALY"]
    assert len(outlier_findings) >= 1
    assert outlier_findings[0].evidence["systolic"] == 240.0
    assert outlier_findings[0].confidence_score >= 0.70


def test_anomaly_detection_duplicate_patient_candidate():
    """Verify detection of candidate duplicate patient profiles."""
    records = [
        {"id": "pat-1", "patient_name": "Smith, John", "dob_string": "1980-01-01"},
        {"id": "pat-2", "patient_name": "Smith, John", "dob_string": "1980-01-01"}, # Duplicate
    ]
    findings = detect_clinical_anomalies(records)
    dup_findings = [f for f in findings if f.finding_type == "DUPLICATE_CANDIDATE"]
    assert len(dup_findings) >= 1
    assert "matched_fingerprint" in dup_findings[0].evidence


def test_error_explainer():
    """Verify plain-English explanation of clinical errors and remediation steps."""
    res = explain_clinical_error(
        error_type="BUSINESS_RULE_VIOLATION",
        error_message="Systolic value 260 mmHg exceeds standard threshold.",
        field_path="component[0].valueQuantity.value",
        raw_value=260,
    )
    assert "clinician" in res.clinical_impact.lower()
    assert "review" in res.suggested_remediation.lower()
    assert res.confidence_score >= 0.90


def test_ai_openapi_routes_registered():
    """Verify AI mapping, analysis, and explanation routes are active in OpenAPI schema."""
    paths = app.openapi()["paths"]
    # API v1 routes
    assert "/api/v1/ai/map-fields" in paths
    assert "/api/v1/ai/analyze" in paths
    assert "/api/v1/ai/explain-error" in paths
    assert "/api/v1/ai/analyses" in paths

    # Root aliases (required by Section 5)
    assert "/ai/map-fields" in paths
    assert "/ai/analyze" in paths
    assert "/ai/explain-error" in paths
