import difflib
from typing import Dict, Any, List, Tuple, Optional

from app.schemas.ai import FieldMappingSuggestion, FieldMappingResponse
from app.services.normalization.normalizer import detect_resource_type

# Standard clinical field mapping knowledge base
KNOWLEDGE_BASE: Dict[str, Dict[str, Tuple[str, float, str]]] = {
    "Patient": {
        "mrn": ("identifier[0].value", 0.98, "Exact Medical Record Number identifier"),
        "patient_id": ("identifier[0].value", 0.96, "Primary patient ID key"),
        "vendor_patient_id": ("identifier[0].value", 0.95, "Proprietary vendor patient key"),
        "pat_id": ("identifier[0].value", 0.92, "Common abbreviation for patient ID"),
        "chart_number": ("identifier[0].value", 0.90, "Clinical chart index identifier"),
        "first_name": ("name[0].given[0]", 0.96, "Patient given name"),
        "fname": ("name[0].given[0]", 0.92, "Abbreviated first name"),
        "given_name": ("name[0].given[0]", 0.96, "FHIR-aligned given name attribute"),
        "last_name": ("name[0].family", 0.96, "Patient family/surname"),
        "lname": ("name[0].family", 0.92, "Abbreviated last name"),
        "family_name": ("name[0].family", 0.96, "FHIR-aligned family name attribute"),
        "surname": ("name[0].family", 0.95, "Clinical surname attribute"),
        "patient_name": ("name[0].text", 0.90, "Composite full name string requiring parsing"),
        "full_name": ("name[0].text", 0.90, "Composite full name string"),
        "birth_date": ("birthDate", 0.98, "Patient date of birth"),
        "dob": ("birthDate", 0.95, "Standard medical abbreviation for Date of Birth"),
        "dob_string": ("birthDate", 0.92, "Vendor date of birth text format"),
        "date_of_birth": ("birthDate", 0.98, "Explicit date of birth field"),
        "gender": ("gender", 0.97, "Administrative gender"),
        "gender_code": ("gender", 0.94, "Coded gender representation"),
        "sex": ("gender", 0.93, "Biological or administrative sex indicator"),
        "phone": ("telecom[0].value", 0.94, "Telecom contact number"),
        "phone_number": ("telecom[0].value", 0.95, "Telephone contact number"),
        "patient_phone": ("telecom[0].value", 0.95, "Patient telephone contact number"),
        "email": ("telecom[1].value", 0.95, "Electronic mail address"),
        "email_address": ("telecom[1].value", 0.96, "Explicit email attribute"),
        "address": ("address[0].line[0]", 0.90, "Postal street address"),
        "city": ("address[0].city", 0.96, "Municipality or city"),
        "state": ("address[0].state", 0.95, "State or administrative territory"),
        "zip": ("address[0].postalCode", 0.95, "Postal zip code"),
        "postal_code": ("address[0].postalCode", 0.96, "Standard postal code identifier"),
    },
    "Observation": {
        "bp": ("code.coding (LOINC 85354-9)", 0.95, "Compound blood pressure panel string"),
        "blood_pressure": ("code.coding (LOINC 85354-9)", 0.96, "Blood pressure panel identifier"),
        "systolic": ("component[0].valueQuantity (LOINC 8480-6)", 0.97, "Systolic blood pressure component"),
        "sys_bp": ("component[0].valueQuantity (LOINC 8480-6)", 0.94, "Abbreviated systolic blood pressure"),
        "diastolic": ("component[1].valueQuantity (LOINC 8462-4)", 0.97, "Diastolic blood pressure component"),
        "dia_bp": ("component[1].valueQuantity (LOINC 8462-4)", 0.94, "Abbreviated diastolic blood pressure"),
        "heart_rate": ("code.coding (LOINC 8867-4)", 0.96, "Heart rate vital signs code"),
        "pulse": ("code.coding (LOINC 8867-4)", 0.95, "Radial or cardiac pulse measurement"),
        "bpm": ("code.coding (LOINC 8867-4)", 0.92, "Beats-per-minute vital signs code"),
        "blood_sugar": ("code.coding (LOINC 1558-6)", 0.95, "Glucose mass/volume concentration"),
        "glucose": ("code.coding (LOINC 1558-6)", 0.96, "Serum or plasma glucose measurement"),
        "fbs": ("code.coding (LOINC 1558-6)", 0.92, "Fasting blood sugar observation"),
        "temperature": ("code.coding (LOINC 8310-5)", 0.96, "Body temperature measurement"),
        "temp": ("code.coding (LOINC 8310-5)", 0.92, "Abbreviated temperature indicator"),
        "weight": ("code.coding (LOINC 29463-7)", 0.95, "Body weight observation"),
        "height": ("code.coding (LOINC 8302-2)", 0.95, "Body height observation"),
    },
    "Condition": {
        "diagnosis": ("code.text", 0.94, "Primary clinical diagnosis narrative"),
        "condition": ("code.text", 0.92, "Health condition text"),
        "problem": ("code.text", 0.90, "Problem list narrative"),
        "icd10": ("code.coding[0].code (ICD-10)", 0.98, "Standard ICD-10 diagnostic terminology"),
        "icd_code": ("code.coding[0].code (ICD-10)", 0.95, "ICD diagnostic code"),
        "snomed": ("code.coding[0].code (SNOMED-CT)", 0.97, "SNOMED Clinical Terms code"),
        "onset": ("onsetDateTime", 0.94, "Clinical onset timestamp"),
        "diagnosed_date": ("onsetDateTime", 0.95, "Date of initial diagnosis"),
    }
}


def suggest_field_mappings(
    sample_record: Dict[str, Any],
    target_resource_type: Optional[str] = None
) -> FieldMappingResponse:
    """
    AI-driven field mapping recommender.
    Matches unknown external JSON keys against standardized FHIR targets,
    attaching confidence scores and flagging ambiguous mappings for human clinical sign-off.
    """
    res_type = target_resource_type or detect_resource_type(sample_record)
    if res_type not in KNOWLEDGE_BASE:
        res_type = "Patient" # Default domain

    domain_kb = KNOWLEDGE_BASE[res_type]
    suggestions: List[FieldMappingSuggestion] = []
    unmapped_fields: List[str] = []

    # Flatten nested dictionaries 1 level for inspection
    flat_record: Dict[str, Any] = {}
    for k, v in sample_record.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                flat_record[f"{k}.{sub_k}"] = sub_v
        else:
            flat_record[k] = v

    total_conf = 0.0

    for source_key, sample_val in flat_record.items():
        # Clean key for matching (strip prefixes, lowercase, replace separators)
        search_key = source_key.split(".")[-1].lower().strip().replace("-", "_").replace(" ", "_")

        # 1. Exact Knowledge Base Match
        if search_key in domain_kb:
            target_field, conf, reason = domain_kb[search_key]
            suggestions.append(
                FieldMappingSuggestion(
                    source_field=source_key,
                    suggested_target_field=target_field,
                    fhir_resource_type=res_type,
                    confidence_score=conf,
                    requires_human_approval=(conf < 0.85),
                    mapping_reason=reason,
                    sample_source_value=sample_val,
                )
            )
            total_conf += conf
            continue

        # 1b. Check stripped domain prefix (e.g. patient_phone -> phone, client_dob -> dob)
        stripped_key = search_key
        for prefix in ["patient_", "pat_", "client_", "vendor_", "user_"]:
            if stripped_key.startswith(prefix):
                stripped_key = stripped_key[len(prefix):]
                break

        if stripped_key in domain_kb:
            target_field, conf, reason = domain_kb[stripped_key]
            score = round(conf * 0.98, 2)
            suggestions.append(
                FieldMappingSuggestion(
                    source_field=source_key,
                    suggested_target_field=target_field,
                    fhir_resource_type=res_type,
                    confidence_score=score,
                    requires_human_approval=(score < 0.85),
                    mapping_reason=f"Matched attribute '{stripped_key}': {reason}",
                    sample_source_value=sample_val,
                )
            )
            total_conf += score
            continue

        # 2. Fuzzy String & Substring Match
        best_match = None
        best_ratio = 0.0
        best_target = None
        best_reason = None

        for kb_key, (target_field, base_conf, reason) in domain_kb.items():
            ratio = difflib.SequenceMatcher(None, search_key, kb_key).ratio()
            if search_key in kb_key or kb_key in search_key:
                ratio = max(ratio, 0.78)

            if ratio > best_ratio and ratio >= 0.60:
                best_ratio = ratio
                best_target = target_field
                best_match = kb_key
                best_reason = f"Fuzzy linguistic match with '{kb_key}' ({int(ratio * 100)}% similarity)"

        if best_match and best_target:
            score = round(best_ratio * 0.90, 2)
            suggestions.append(
                FieldMappingSuggestion(
                    source_field=source_key,
                    suggested_target_field=best_target,
                    fhir_resource_type=res_type,
                    confidence_score=score,
                    requires_human_approval=(score < 0.85), # Human in the loop requirement
                    mapping_reason=best_reason or "Probabilistic match",
                    sample_source_value=sample_val,
                )
            )
            total_conf += score
        else:
            unmapped_fields.append(source_key)

    overall_confidence = round(total_conf / len(suggestions), 2) if suggestions else 0.0

    return FieldMappingResponse(
        resource_type=res_type,
        overall_confidence=overall_confidence,
        suggestions=suggestions,
        unmapped_fields=unmapped_fields,
    )
