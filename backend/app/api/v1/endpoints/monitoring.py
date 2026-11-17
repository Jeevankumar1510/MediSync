from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_engineer, require_any_authenticated
from app.database import get_db
from app.models.user import User
from app.models.sync_job import SyncJob, SyncJobStatus
from app.models.audit import AuditLog
from app.schemas.sync import SyncStatisticsResponse

router = APIRouter()


@router.get(
    "/sync-statistics",
    response_model=SyncStatisticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Synchronization Health & Metrics",
    description="Calculates comprehensive metrics across all background synchronization jobs, including success rate and processed records.",
)
async def get_sync_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
):
    # Total jobs count
    total_q = select(func.count(SyncJob.id))
    total_res = await db.execute(total_q)
    total_jobs = total_res.scalar_one() or 0

    # Counts by status
    completed_q = select(func.count(SyncJob.id)).where(SyncJob.status == SyncJobStatus.COMPLETED)
    completed_res = await db.execute(completed_q)
    completed_jobs = completed_res.scalar_one() or 0

    failed_q = select(func.count(SyncJob.id)).where(SyncJob.status == SyncJobStatus.FAILED)
    failed_res = await db.execute(failed_q)
    failed_jobs = failed_res.scalar_one() or 0

    running_q = select(func.count(SyncJob.id)).where(SyncJob.status == SyncJobStatus.RUNNING)
    running_res = await db.execute(running_q)
    running_jobs = running_res.scalar_one() or 0

    pending_q = select(func.count(SyncJob.id)).where(SyncJob.status == SyncJobStatus.PENDING)
    pending_res = await db.execute(pending_q)
    pending_jobs = pending_res.scalar_one() or 0

    # Total records processed sum
    sum_q = select(func.coalesce(func.sum(SyncJob.records_processed), 0))
    sum_res = await db.execute(sum_q)
    total_records = sum_res.scalar_one() or 0

    # Success rate
    rate = round((completed_jobs / total_jobs * 100), 1) if total_jobs > 0 else 100.0

    return SyncStatisticsResponse(
        total_jobs=total_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        running_jobs=running_jobs,
        pending_jobs=pending_jobs,
        total_records_synced=total_records,
        success_rate_percentage=rate,
    )


@router.get(
    "/api-logs",
    status_code=status.HTTP_200_OK,
    summary="Get System API & Audit Logs",
    description="Retrieves security audit logs and healthcare API transaction records for system monitoring.",
)
async def get_api_logs(
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None, description="Filter by action (e.g. LOGIN_SUCCESS, SYNC_TRIGGER, PATIENT_READ)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action.upper())

    query = query.order_by(AuditLog.created_at.desc()).limit(limit)
    res = await db.execute(query)
    logs = res.scalars().all()

    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "ip_address": log.ip_address,
            "details": log.details,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
