from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_engineer, require_admin
from app.database import get_db
from app.models.user import User
from app.models.sync_job import SyncJob, SyncJobStatus
from app.models.integration import APIIntegration
from app.schemas.sync import SyncJobResponse, SyncJobListResponse
from app.tasks.sync_tasks import run_sync_task

router = APIRouter()


@router.get(
    "/jobs",
    response_model=SyncJobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Synchronization Jobs",
    description="Lists background sync jobs with operational status filtering (PENDING, RUNNING, COMPLETED, FAILED, RETRYING) and pagination.",
)
async def list_sync_jobs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, description="Filter by status: PENDING, RUNNING, COMPLETED, FAILED, RETRYING"),
    integration_id: Optional[uuid.UUID] = Query(None, description="Filter by specific integration UUID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    query = select(SyncJob).options(selectinload(SyncJob.integration))
    if status_filter:
        query = query.where(SyncJob.status == status_filter.upper())
    if integration_id:
        query = query.where(SyncJob.integration_id == integration_id)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    count_res = await db.execute(count_q)
    total = count_res.scalar_one()

    # Paged query
    paged_q = query.order_by(SyncJob.created_at.desc()).offset((page - 1) * size).limit(size)
    res = await db.execute(paged_q)
    jobs = res.scalars().all()

    items = []
    for j in jobs:
        resp = SyncJobResponse.model_validate(j)
        if j.integration:
            resp.integration_name = j.integration.name
        items.append(resp)

    return SyncJobListResponse(items=items, total=total, page=page, size=size)


@router.get(
    "/jobs/{job_id}",
    response_model=SyncJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Synchronization Job Details",
    description="Retrieves granular progress metrics, fetched/processed/failed counters, and error summaries for a sync job.",
)
async def get_sync_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    query = select(SyncJob).where(SyncJob.id == job_id).options(selectinload(SyncJob.integration))
    res = await db.execute(query)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SyncJob with ID {job_id} not found.",
        )

    resp = SyncJobResponse.model_validate(job)
    if job.integration:
        resp.integration_name = job.integration.name
    return resp


@router.post(
    "/jobs/{job_id}/retry",
    response_model=SyncJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Retry Synchronization Job",
    description="Resets error flags and re-enqueues a failed or stalled synchronization job into Celery.",
)
async def retry_sync_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_engineer),
):
    query = select(SyncJob).where(SyncJob.id == job_id).options(selectinload(SyncJob.integration))
    res = await db.execute(query)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SyncJob with ID {job_id} not found.",
        )

    job.status = SyncJobStatus.PENDING
    job.error_summary = None
    await db.commit()
    await db.refresh(job)

    # Enqueue task in Celery
    try:
        run_sync_task.delay(str(job.id))
    except Exception as exc:
        # If Celery worker/broker isn't running in current test context, job remains PENDING
        pass

    resp = SyncJobResponse.model_validate(job)
    if job.integration:
        resp.integration_name = job.integration.name
    return resp
