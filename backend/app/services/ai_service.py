import logging
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analysis import AIAnalysis, AnalysisType, AnalysisReviewStatus
from app.models.patient import PatientRecord
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.ai import (
    FieldMappingRequest,
    FieldMappingResponse,
    DataQualityAnalyzeRequest,
    DataQualityAnalyzeResponse,
    ExplainErrorRequest,
    ExplainErrorResponse,
    AIAnalysisResponse,
)
from app.services.ai.field_mapper import suggest_field_mappings
from app.services.ai.anomaly_detector import detect_clinical_anomalies
from app.services.ai.error_explainer import explain_clinical_error

logger = logging.getLogger("medisync.ai_service")


async def execute_field_mapping(
    sample_record: Dict[str, Any],
    target_resource_type: Optional[str] = None,
    db: Optional[AsyncSession] = None,
    user_id: Optional[uuid.UUID] = None,
) -> FieldMappingResponse:
    """Executes AI field mapping recommendation and records suggestion history for human review."""
    result = suggest_field_mappings(sample_record, target_resource_type)

    if db:
        analysis_record = AIAnalysis(
            target_type="FIELD_MAPPING",
            target_id=None,
            analysis_type=AnalysisType.FIELD_MAPPING,
            confidence_score=result.overall_confidence,
            findings=result.model_dump(),
            status=AnalysisReviewStatus.PENDING_REVIEW,
        )
        db.add(analysis_record)
        await db.commit()
        await db.refresh(analysis_record)
        result.analysis_id = analysis_record.id

    return result


async def execute_data_quality_analysis(
    req: DataQualityAnalyzeRequest,
    db: Optional[AsyncSession] = None,
    user_id: Optional[uuid.UUID] = None,
) -> DataQualityAnalyzeResponse:
    """
    Runs multi-variate Scikit-learn anomaly detection, duplicate detection, and missing-field scans.
    Persists findings for clinical auditing. Never mutates clinical data automatically.
    """
    records_to_analyze: List[Dict[str, Any]] = req.records or []

    # If records not passed in payload, fetch from DB
    if not records_to_analyze and db:
        query = select(PatientRecord)
        if req.patient_id:
            query = query.where(PatientRecord.patient_id == req.patient_id)
        if req.integration_id:
            query = query.where(PatientRecord.integration_id == req.integration_id)
        query = query.limit(100)
        res = await db.execute(query)
        db_records = res.scalars().all()
        records_to_analyze = [r.raw_payload for r in db_records]

    findings = detect_clinical_anomalies(records_to_analyze)

    analysis_id = uuid.uuid4()
    if db:
        avg_conf = (
            round(sum(f.confidence_score for f in findings) / len(findings), 2)
            if findings
            else 1.0
        )
        analysis_record = AIAnalysis(
            id=analysis_id,
            target_type="PATIENT_RECORD" if req.patient_id else "INTEGRATION",
            target_id=req.patient_id or req.integration_id,
            analysis_type=AnalysisType.ANOMALY_DETECTION,
            confidence_score=avg_conf,
            findings={"findings": [f.model_dump() for f in findings]},
            status=AnalysisReviewStatus.PENDING_REVIEW,
        )
        db.add(analysis_record)
        await db.commit()

    return DataQualityAnalyzeResponse(
        analysis_id=analysis_id,
        records_analyzed=len(records_to_analyze),
        anomaly_count=len(findings),
        findings=findings,
        created_at=datetime.now(timezone.utc),
    )


def execute_explain_error(req: ExplainErrorRequest) -> ExplainErrorResponse:
    """Provides plain-language clinical and technical explanations for validation errors."""
    return explain_clinical_error(
        error_type=req.error_type,
        error_message=req.error_message,
        field_path=req.field_path,
        raw_value=req.raw_value,
        resource_type=req.resource_type or "Observation",
    )


async def review_analysis(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    review_status: AnalysisReviewStatus,
    current_user: User,
    notes: Optional[str] = None,
) -> AIAnalysisResponse:
    """Human-in-the-loop review approval or rejection of AI mapping/anomaly recommendations."""
    analysis = await db.get(AIAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AIAnalysis with ID {analysis_id} not found.",
        )

    analysis.status = review_status
    analysis.reviewed_by_user_id = current_user.id
    analysis.review_notes = notes

    audit_entry = AuditLog(
        user_id=current_user.id,
        action=f"AI_ANALYSIS_{review_status.value}",
        resource_type="AIAnalysis",
        resource_id=str(analysis.id),
        details={"status": review_status.value, "notes": notes},
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(analysis)

    return AIAnalysisResponse.model_validate(analysis)


async def list_analyses(
    db: AsyncSession,
    analysis_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    size: int = 20,
) -> List[AIAnalysisResponse]:
    """Retrieves paginated AI analysis and field mapping recommendation history."""
    query = select(AIAnalysis)
    if analysis_type:
        query = query.where(AIAnalysis.analysis_type == analysis_type.upper())
    if status_filter:
        query = query.where(AIAnalysis.status == status_filter.upper())

    query = query.order_by(AIAnalysis.created_at.desc()).offset((page - 1) * size).limit(size)
    res = await db.execute(query)
    items = res.scalars().all()
    return [AIAnalysisResponse.model_validate(i) for i in items]
