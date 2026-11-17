from typing import Any, Optional

from app.schemas.ai import ExplainErrorResponse

ERROR_KNOWLEDGE_BASE = {
    "MISSING_FIELD": {
        "explanation": "A mandatory HL7 FHIR element was omitted from the payload during external transmission.",
        "clinical_impact": "Downstream clinical decision support (CDS) algorithms may fail or produce inaccurate patient risk assessments.",
        "remediation": "Update the source integration pipeline or mapping configuration to map the required attribute, or set a compliant fallback default."
    },
    "BUSINESS_RULE_VIOLATION": {
        "explanation": "A clinical measurement value violates standard physiological plausibility boundaries (e.g. human systolic blood pressure > 300 mmHg).",
        "clinical_impact": "Signals potential sensor artifact, equipment calibration failure, or typographical data entry error that could mislead clinicians.",
        "remediation": "Flag record for clinical nurse or physician review. Check EHR data source equipment logs before re-authorizing the record."
    },
    "TYPE_MISMATCH": {
        "explanation": "The data type received does not match the target FHIR specification (e.g., received a string when a float or integer was required).",
        "clinical_impact": "Prevents automated parsing by electronic health record systems and analytics warehouses, resulting in lost clinical encounters.",
        "remediation": "Apply a type casting transformer (e.g., float() or int()) in the normalization pipeline before committing to the database."
    },
    "INVALID_FHIR": {
        "explanation": "The resource violates core HL7 FHIR Release 4 specification rules, such as invalid administrative gender or unrecognized status codes.",
        "clinical_impact": "External FHIR gateways and health information exchanges (HIE) will reject the transaction bundle during interoperability exchange.",
        "remediation": "Ensure coded values strictly align with HL7 standard ValueSets (e.g., male, female, other, unknown for administrative gender)."
    },
    "DUPLICATE": {
        "explanation": "An identical record with the same cryptographic SHA-256 checksum has already been ingested into the system.",
        "clinical_impact": "Duplicate clinical records distort patient histories, double-count vital sign trends, and inflate reporting statistics.",
        "remediation": "The idempotency filter has safely preserved the original record. Verify that external pollers or webhooks are not generating redundant events."
    }
}


def explain_clinical_error(
    error_type: str,
    error_message: str,
    field_path: str,
    raw_value: Optional[Any] = None,
    resource_type: str = "Observation",
) -> ExplainErrorResponse:
    """
    Translates cryptic validation exceptions into clear, clinically actionable explanations
    with root causes, clinical risk assessments, and concrete remediation steps.
    """
    clean_type = error_type.upper().strip()
    kb_entry = ERROR_KNOWLEDGE_BASE.get(
        clean_type,
        {
            "explanation": f"A data validation error occurred on field '{field_path}': {error_message}",
            "clinical_impact": "Record integrity cannot be guaranteed without verification.",
            "remediation": f"Inspect the raw input ({raw_value}) and adjust the mapping configuration."
        }
    )

    # Customize explanation with field and raw value context
    custom_explanation = (
        f"{kb_entry['explanation']} "
        f"Specifically, field '{field_path}' failed with: '{error_message}'."
    )
    if raw_value is not None:
        custom_explanation += f" (Observed raw value: {raw_value})"

    return ExplainErrorResponse(
        explanation=custom_explanation,
        clinical_impact=kb_entry["clinical_impact"],
        suggested_remediation=kb_entry["remediation"],
        confidence_score=0.96,
    )
