from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_any_authenticated, require_analyst, require_engineer
from app.database import get_db
from app.models.user import User
from app.models.ai_analysis import AnalysisReviewStatus
from app.schemas.ai import (
    FieldMappingRequest,
    FieldMappingResponse,
    DataQualityAnalyzeRequest,
    DataQualityAnalyzeResponse,
    ExplainErrorRequest,
    ExplainErrorResponse,
    AIAnalysisReviewRequest,
    AIAnalysisResponse,
)
from app.services import ai_service

router = APIRouter()


@router.post(
    "/map-fields",
    response_model=FieldMappingResponse,
    status_code=status.HTTP_200_OK,
    summary="AI Field Mapping Recommender",
    description="Analyzes unknown external healthcare JSON and suggests mappings to standardized FHIR fields with confidence scores and human-approval flags.",
)
async def map_fields(
    request: FieldMappingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    return await ai_service.execute_field_mapping(
        sample_record=request.sample_record,
        target_resource_type=request.target_resource_type,
        db=db,
        user_id=current_user.id,
    )


@router.post(
    "/analyze",
    response_model=DataQualityAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="AI Clinical Data Quality Analysis",
    description="Executes Scikit-learn IsolationForest outlier detection, duplicate record scans, and missing-field evaluations without modifying records.",
)
async def analyze_data_quality(
    request: DataQualityAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    return await ai_service.execute_data_quality_analysis(
        req=request,
        db=db,
        user_id=current_user.id,
    )


@router.post(
    "/explain-error",
    response_model=ExplainErrorResponse,
    status_code=status.HTTP_200_OK,
    summary="Explain Validation Error in Plain English",
    description="Translates cryptic validation codes into plain-language clinical explanations, clinical risk assessments, and remediation steps.",
)
def explain_error(
    request: ExplainErrorRequest,
    current_user: User = Depends(require_any_authenticated),
):
    return ai_service.execute_explain_error(request)


@router.get(
    "/analyses",
    response_model=List[AIAnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="List AI Quality Findings & Mapping History",
    description="Retrieves historical AI findings, confidence metrics, and human review decisions.",
)
async def list_analyses(
    analysis_type: Optional[str] = Query(None, description="DATA_QUALITY | ANOMALY_DETECTION | FIELD_MAPPING"),
    status: Optional[str] = Query(None, description="PENDING_REVIEW | APPROVED | REJECTED | AUTO_APPLIED"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    return await ai_service.list_analyses(
        db=db,
        analysis_type=analysis_type,
        status_filter=status,
        page=page,
        size=size,
    )


@router.post(
    "/analyses/{analysis_id}/approve",
    response_model=AIAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Human-in-the-Loop Review: Approve",
    description="Approves recommended AI field mappings or acknowledges clinical anomaly findings.",
)
async def approve_analysis(
    analysis_id: uuid.UUID,
    review_in: AIAnalysisReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    return await ai_service.review_analysis(
        db=db,
        analysis_id=analysis_id,
        review_status=AnalysisReviewStatus.APPROVED,
        current_user=current_user,
        notes=review_in.notes,
    )


@router.post(
    "/analyses/{analysis_id}/reject",
    response_model=AIAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Human-in-the-Loop Review: Reject",
    description="Rejects recommended AI field mappings or dismisses clinical anomaly findings with feedback notes.",
)
async def reject_analysis(
    analysis_id: uuid.UUID,
    review_in: AIAnalysisReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    return await ai_service.review_analysis(
        db=db,
        analysis_id=analysis_id,
        review_status=AnalysisReviewStatus.REJECTED,
        current_user=current_user,
        notes=review_in.notes,
    )
