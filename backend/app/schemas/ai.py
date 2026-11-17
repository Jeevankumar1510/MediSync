from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid
from pydantic import BaseModel, Field, ConfigDict

from app.models.ai_analysis import AnalysisType, AnalysisReviewStatus


class FieldMappingSuggestion(BaseModel):
    source_field: str = Field(..., description="Field key from vendor payload")
    suggested_target_field: str = Field(..., description="Target standardized FHIR path (e.g. name[0].family)")
    fhir_resource_type: str = Field(..., description="Patient | Observation | Condition")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    requires_human_approval: bool = Field(..., description="True if confidence < 0.85")
    mapping_reason: str = Field(..., description="Semantic or pattern matching justification")
    sample_source_value: Optional[Any] = None


class FieldMappingRequest(BaseModel):
    sample_record: Dict[str, Any] = Field(..., description="Vendor JSON record to analyze")
    target_resource_type: Optional[str] = Field(None, description="Optional target FHIR resourceType (Patient, Observation, Condition)")


class FieldMappingResponse(BaseModel):
    resource_type: str
    overall_confidence: float
    suggestions: List[FieldMappingSuggestion]
    unmapped_fields: List[str] = Field(default_factory=list)
    analysis_id: Optional[uuid.UUID] = None


class DataQualityFinding(BaseModel):
    finding_type: str = Field(..., description="OUTLIER_ANOMALY | MISSING_FIELD | DUPLICATE_CANDIDATE | INCONSISTENT_FORMAT")
    severity: str = Field(..., description="CRITICAL | WARNING | INFO")
    field_name: str
    explanation: str
    confidence_score: float
    evidence: Dict[str, Any]


class DataQualityAnalyzeRequest(BaseModel):
    records: Optional[List[Dict[str, Any]]] = Field(None, description="In-memory list of clinical records to analyze")
    patient_id: Optional[uuid.UUID] = Field(None, description="Analyze records stored for a specific patient UUID")
    integration_id: Optional[uuid.UUID] = Field(None, description="Analyze records ingested from an integration UUID")


class DataQualityAnalyzeResponse(BaseModel):
    analysis_id: uuid.UUID
    records_analyzed: int
    anomaly_count: int
    findings: List[DataQualityFinding]
    created_at: datetime


class ExplainErrorRequest(BaseModel):
    error_type: str = Field(..., description="e.g. MISSING_FIELD, TYPE_MISMATCH, INVALID_FHIR")
    error_message: str = Field(..., description="Validation failure message")
    field_path: str = Field(..., description="Field path (e.g. component[0].valueQuantity.value)")
    raw_value: Optional[Any] = None
    resource_type: Optional[str] = "Observation"


class ExplainErrorResponse(BaseModel):
    explanation: str
    clinical_impact: str
    suggested_remediation: str
    confidence_score: float


class AIAnalysisReviewRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000, description="Clinical analyst or engineer review notes")


class AIAnalysisResponse(BaseModel):
    id: uuid.UUID
    target_type: str
    target_id: Optional[uuid.UUID] = None
    analysis_type: str
    confidence_score: float
    findings: Dict[str, Any]
    status: str
    reviewed_by_user_id: Optional[uuid.UUID] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
