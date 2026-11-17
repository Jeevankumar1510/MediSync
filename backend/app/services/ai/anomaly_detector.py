import logging
from typing import Dict, Any, List, Optional
import numpy as np
from sklearn.ensemble import IsolationForest

from app.schemas.ai import DataQualityFinding

logger = logging.getLogger("medisync.anomaly_detector")

# Baseline reference distribution for normal human vitals (Synthea/CDC standard ranges)
# Features: [Systolic, Diastolic, Heart Rate, Fasting Glucose]
BASELINE_VITALS_NORMAL = np.array([
    [118, 78, 72, 92],
    [120, 80, 70, 95],
    [122, 82, 75, 98],
    [115, 75, 68, 88],
    [125, 84, 76, 102],
    [130, 85, 80, 105],
    [110, 70, 65, 85],
    [128, 82, 74, 99],
    [116, 76, 71, 91],
    [121, 79, 73, 94],
])


def detect_clinical_anomalies(records: List[Dict[str, Any]]) -> List[DataQualityFinding]:
    """
    Applies Scikit-learn IsolationForest and heuristic clinical checks
    to detect statistical outliers, missing clinical elements, and duplicate records.
    Never mutates records automatically.
    """
    findings: List[DataQualityFinding] = []
    if not records:
        return findings

    # 1. Multi-Variate Outlier Detection via Isolation Forest
    vitals_matrix: List[List[float]] = []
    record_map: List[Dict[str, Any]] = []

    for rec in records:
        # Extract systolic & diastolic
        systolic = None
        diastolic = None
        hr = None
        glucose = None

        # Check raw payload or components
        if "bp" in rec and "/" in str(rec["bp"]):
            try:
                parts = str(rec["bp"]).split("/")
                systolic = float(parts[0])
                diastolic = float(parts[1])
            except ValueError:
                pass
        elif "systolic" in rec and "diastolic" in rec:
            try:
                systolic = float(rec["systolic"])
                diastolic = float(rec["diastolic"])
            except ValueError:
                pass

        if "heart_rate" in rec or "bpm" in rec:
            try:
                hr = float(rec.get("heart_rate") or rec.get("bpm"))
            except ValueError:
                pass

        if "glucose" in rec or "blood_sugar" in rec:
            try:
                glucose = float(rec.get("glucose") or rec.get("blood_sugar"))
            except ValueError:
                pass

        if systolic is not None and diastolic is not None:
            vitals_matrix.append([
                systolic,
                diastolic,
                hr if hr is not None else 72.0,
                glucose if glucose is not None else 95.0,
            ])
            record_map.append(rec)

    # Train IsolationForest against baseline normal values + incoming sample points
    if len(vitals_matrix) > 0:
        sample_matrix = np.array(vitals_matrix)
        training_data = np.vstack([BASELINE_VITALS_NORMAL, sample_matrix])

        # Contamination rate: expect ~10% statistical anomalies
        clf = IsolationForest(contamination=0.15, random_state=42)
        clf.fit(training_data)
        predictions = clf.predict(sample_matrix)
        scores = clf.decision_function(sample_matrix)

        for idx, (pred, score) in enumerate(zip(predictions, scores)):
            if pred == -1: # Outlier detected by Isolation Forest
                vitals_row = sample_matrix[idx]
                target_rec = record_map[idx]
                confidence = round(float(np.clip(abs(score) * 2 + 0.5, 0.65, 0.99)), 2)
                findings.append(
                    DataQualityFinding(
                        finding_type="OUTLIER_ANOMALY",
                        severity="WARNING" if vitals_row[0] < 200 else "CRITICAL",
                        field_name="vitals (Blood Pressure / Heart Rate)",
                        explanation=(
                            f"Multi-variate statistical anomaly detected by IsolationForest. "
                            f"Vitals signature (Systolic: {vitals_row[0]}, Diastolic: {vitals_row[1]}) "
                            f"diverges significantly from expected population cluster."
                        ),
                        confidence_score=confidence,
                        evidence={
                            "systolic": vitals_row[0],
                            "diastolic": vitals_row[1],
                            "anomaly_score": round(float(score), 4),
                            "record_id": target_rec.get("id", "Unknown"),
                        },
                    )
                )

    # 2. Missing Mandatory Fields Analysis
    for rec in records:
        r_type = rec.get("resourceType") or "Patient"
        if r_type == "Patient":
            if not rec.get("birthDate") and not rec.get("dob_string") and not rec.get("birth_date"):
                findings.append(
                    DataQualityFinding(
                        finding_type="MISSING_FIELD",
                        severity="WARNING",
                        field_name="birthDate",
                        explanation="Patient demographic profile lacks birth date, impairing age-stratified clinical analytics.",
                        confidence_score=0.95,
                        evidence={"record_id": rec.get("id", "Unknown"), "patient_name": rec.get("patient_name") or rec.get("name")},
                    )
                )
            if not rec.get("mrn") and not rec.get("vendor_patient_id") and not rec.get("identifier"):
                findings.append(
                    DataQualityFinding(
                        finding_type="MISSING_FIELD",
                        severity="CRITICAL",
                        field_name="identifier",
                        explanation="Patient lacks primary Medical Record Number (MRN), risking unlinked clinical records.",
                        confidence_score=0.99,
                        evidence={"record_id": rec.get("id", "Unknown")},
                    )
                )

    # 3. Duplicate Record Candidate Detection
    seen_identities: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        name_key = str(rec.get("patient_name") or rec.get("last_name", "") + rec.get("first_name", "")).strip().lower()
        dob_key = str(rec.get("birthDate") or rec.get("dob_string") or "").strip()
        if name_key and dob_key:
            identity_fingerprint = f"{name_key}|{dob_key}"
            if identity_fingerprint in seen_identities:
                prev = seen_identities[identity_fingerprint]
                findings.append(
                    DataQualityFinding(
                        finding_type="DUPLICATE_CANDIDATE",
                        severity="WARNING",
                        field_name="patient_identity",
                        explanation=(
                            f"Probable duplicate patient record detected. Record matches "
                            f"previous entry on both Name and Date of Birth."
                        ),
                        confidence_score=0.92,
                        evidence={
                            "matched_fingerprint": identity_fingerprint,
                            "current_id": rec.get("id", "Unknown"),
                            "existing_id": prev.get("id", "Unknown"),
                        },
                    )
                )
            else:
                seen_identities[identity_fingerprint] = rec

    return findings
