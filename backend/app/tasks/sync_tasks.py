import logging
import uuid
from celery import shared_task

from app.core.celery_app import celery_app
from app.services.sync_engine import execute_synchronization
from app.database import get_sync_db
from app.models.integration import APIIntegration, IntegrationStatus
from app.models.sync_job import SyncJob, SyncJobType, SyncJobStatus

logger = logging.getLogger("medisync.celery_tasks")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_sync_task(self, job_id_str: str):
    """
    Asynchronous Celery task orchestrating healthcare API synchronization.
    Features automatic exponential backoff retry on temporary network failure.
    """
    logger.info(f"Celery executing sync task for Job ID: {job_id_str}")
    try:
        job_id = uuid.UUID(job_id_str)
        result = execute_synchronization(job_id)
        if not result.get("success"):
            # Trigger exponential backoff retry
            countdown = 2 ** self.request.retries * 15 # 15s, 30s, 60s
            logger.warning(f"Task {job_id_str} failed. Retrying in {countdown} seconds...")
            raise self.retry(countdown=countdown, exc=Exception(result.get("error", "Unknown sync error")))
        return result
    except Exception as exc:
        logger.error(f"Unrecoverable error in sync task {job_id_str}: {exc}")
        raise exc


@celery_app.task
def scheduled_sync_all_active_integrations():
    """Periodic Celery beat task to poll all ACTIVE integrations automatically."""
    logger.info("Executing scheduled sync for all active healthcare integrations...")
    with get_sync_db() as db:
        active_integrations = (
            db.query(APIIntegration)
            .filter(APIIntegration.status == IntegrationStatus.ACTIVE)
            .all()
        )
        enqueued = 0
        for integ in active_integrations:
            job = SyncJob(
                integration_id=integ.id,
                job_type=SyncJobType.SCHEDULED_POLL,
                status=SyncJobStatus.PENDING,
            )
            db.add(job)
            db.flush()
            run_sync_task.delay(str(job.id))
            enqueued += 1

        db.commit()
        logger.info(f"Scheduled sync enqueued {enqueued} integration jobs.")
        return {"enqueued": enqueued}
