import logging
import uuid
from celery import shared_task

from app.core.celery_app import celery_app
from app.services.webhook_service import process_webhook_record

logger = logging.getLogger("medisync.webhook_tasks")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=20)
def process_webhook_event_task(self, event_id_str: str):
    """
    Celery background worker task for asynchronous webhook event processing.
    """
    logger.info(f"Celery processing webhook event: {event_id_str}")
    try:
        event_uuid = uuid.UUID(event_id_str)
        result = process_webhook_record(event_uuid)
        if not result.get("success"):
            countdown = 2 ** self.request.retries * 15
            logger.warning(f"Webhook task {event_id_str} failed. Retrying in {countdown}s...")
            raise self.retry(countdown=countdown, exc=Exception(result.get("error", "Unknown webhook processing error")))
        return result
    except Exception as exc:
        logger.error(f"Failed processing webhook task {event_id_str}: {exc}")
        raise exc
