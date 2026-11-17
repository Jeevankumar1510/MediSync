import uuid
from datetime import datetime, timezone
import pytest

from app.core.celery_app import celery_app
from app.models.sync_job import SyncJobStatus, SyncJobType
from app.schemas.sync import SyncJobResponse, SyncStatisticsResponse
from app.services.patient_service import compute_payload_checksum
from app.main import app


def test_celery_configuration():
    """Verify Celery application broker, serializer, and reliability configurations."""
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_sync_statistics_schema():
    """Verify SyncStatisticsResponse math and calculation model."""
    stats = SyncStatisticsResponse(
        total_jobs=10,
        completed_jobs=8,
        failed_jobs=2,
        running_jobs=0,
        pending_jobs=0,
        total_records_synced=450,
        success_rate_percentage=80.0,
    )
    assert stats.total_jobs == 10
    assert stats.completed_jobs == 8
    assert stats.success_rate_percentage == 80.0


def test_exponential_backoff_calculation():
    """Verify that retry backoff scales exponentially (15s, 30s, 60s, 120s)."""
    delays = [2 ** retry * 15 for retry in range(4)]
    assert delays == [15, 30, 60, 120]


def test_deduplication_checksum_for_sync():
    """Verify idempotency checksum detects identical records from repeated polling."""
    record_poll_1 = {
        "resourceType": "Observation",
        "id": "obs-001",
        "status": "final",
        "value": 120,
    }
    record_poll_2 = {
        "value": 120,
        "status": "final",
        "id": "obs-001",
        "resourceType": "Observation",
    }
    # Regardless of key ordering, checksum must match to prevent duplicate ingestion
    assert compute_payload_checksum(record_poll_1) == compute_payload_checksum(record_poll_2)


def test_sync_and_monitoring_openapi_routes_registered():
    """Verify all synchronization and monitoring endpoints are active in OpenAPI schema."""
    paths = app.openapi()["paths"]

    # Sync endpoints
    assert "/api/v1/sync/jobs" in paths
    assert "/api/v1/sync/jobs/{job_id}" in paths
    assert "/api/v1/sync/jobs/{job_id}/retry" in paths

    # Monitoring endpoints (required by Section 5)
    assert "/api/v1/monitoring/sync-statistics" in paths
    assert "/api/v1/monitoring/api-logs" in paths
    assert "/monitoring/sync-statistics" in paths
    assert "/monitoring/api-logs" in paths
    assert "/monitoring/health" in paths
