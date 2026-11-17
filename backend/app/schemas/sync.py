from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field, ConfigDict


class SyncJobResponse(BaseModel):
    id: uuid.UUID
    integration_id: uuid.UUID
    integration_name: Optional[str] = None
    job_type: str
    status: str
    records_fetched: int = 0
    records_processed: int = 0
    records_failed: int = 0
    retry_count: int = 0
    max_retries: int = 3
    error_summary: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SyncStatisticsResponse(BaseModel):
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    running_jobs: int = 0
    pending_jobs: int = 0
    total_records_synced: int = 0
    success_rate_percentage: float = 0.0


class SyncJobListResponse(BaseModel):
    items: List[SyncJobResponse]
    total: int
    page: int
    size: int
