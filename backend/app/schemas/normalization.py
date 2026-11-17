from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid
from pydantic import BaseModel, Field, ConfigDict

from app.models.validation import ValidationErrorType, ValidationSeverity


class ValidationIssue(BaseModel):
    field_path: str = Field(..., description="Target dot-notation path in FHIR resource (e.g. subject.reference)")
    error_type: ValidationErrorType = Field(ValidationErrorType.INVALID_FHIR, description="Class of validation anomaly")
    severity: ValidationSeverity = Field(ValidationSeverity.WARNING, description="Severity: CRITICAL | WARNING | INFO")
    message: str = Field(..., description="Human-readable clinical or structural validation diagnostic")
    raw_value: Optional[Any] = Field(None, description="The non-compliant raw value extracted")


class NormalizeRequest(BaseModel):
    source_type: str = Field("AUTO", description="Source vendor format (e.g. MOCK_FHIR, REST_JSON, AUTO)")
    resource_type: Optional[str] = Field(None, description="Target FHIR resource type (Patient, Observation, Condition) or AUTO")
    raw_payload: Dict[str, Any] = Field(..., description="Un-normalized vendor JSON data")


class NormalizeResponse(BaseModel):
    success: bool
    resource_type: str
    checksum: str
    normalized_payload: Dict[str, Any]
    raw_payload: Dict[str, Any]
    is_valid_fhir: bool
    issues: List[ValidationIssue] = Field(default_factory=list)


class ValidateRequest(BaseModel):
    resource_type: str = Field(..., description="Target FHIR resource type (Patient, Observation, Condition)")
    payload: Dict[str, Any] = Field(..., description="Candidate JSON payload to validate against FHIR schema")


class ValidateResponse(BaseModel):
    is_valid: bool
    resource_type: str
    issues: List[ValidationIssue] = Field(default_factory=list)


class ValidationErrorLogResponse(BaseModel):
    id: uuid.UUID
    record_id: Optional[uuid.UUID] = None
    sync_job_id: Optional[uuid.UUID] = None
    resource_type: str
    field_path: str
    error_type: str
    severity: str
    error_message: str
    raw_value: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
