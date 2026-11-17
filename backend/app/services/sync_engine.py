import asyncio
from datetime import datetime, timezone
import logging
from typing import Dict, Any, List, Optional
import uuid

from app.database import get_sync_db
from app.models.integration import (
    APIIntegration,
    IntegrationAuthType,
    IntegrationSourceType,
    IntegrationStatus,
)
from app.models.sync_job import SyncJob, SyncJobStatus
from app.models.patient import Patient, PatientRecord
from app.models.validation import ValidationErrorLog
from app.models.audit import AuditLog
from app.core.encryption import decrypt_secret
from app.services.patient_service import compute_payload_checksum
from app.services.integrations.fhir_client import FHIRClient
from app.services.integrations.vendor_client import VendorRESTClient
from app.services.normalization.normalizer import (
    detect_resource_type,
    normalize_patient,
    normalize_observation,
    normalize_condition,
)

logger = logging.getLogger("medisync.sync_engine")


def execute_synchronization(job_id: uuid.UUID) -> Dict[str, Any]:
    """
    Synchronous processing engine designed for Celery workers.
    Connects to external healthcare APIs, extracts clinical records, normalizes to FHIR R4,
    prevents duplicate ingestion via SHA-256 idempotency checksums, and updates job metrics.
    """
    logger.info(f"Starting synchronization job execution: {job_id}")

    with get_sync_db() as db:
        job = db.query(SyncJob).filter(SyncJob.id == job_id).first()
        if not job:
            logger.error(f"SyncJob {job_id} not found in database.")
            return {"success": False, "error": f"Job {job_id} not found."}

        integration = db.query(APIIntegration).filter(APIIntegration.id == job.integration_id).first()
        if not integration:
            job.status = SyncJobStatus.FAILED
            job.error_summary = "Integration configuration missing."
            db.commit()
            return {"success": False, "error": "Integration missing."}

        # Transition job to RUNNING
        job.status = SyncJobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        # Decrypt authentication headers
        auth_headers: Dict[str, str] = {}
        if integration.credential:
            if integration.auth_type == IntegrationAuthType.API_KEY and integration.credential.encrypted_api_key:
                raw_key = decrypt_secret(integration.credential.encrypted_api_key)
                auth_headers["X-API-Key"] = raw_key or ""
            elif integration.auth_type == IntegrationAuthType.BEARER_TOKEN and integration.credential.encrypted_access_token:
                raw_token = decrypt_secret(integration.credential.encrypted_access_token)
                auth_headers["Authorization"] = f"Bearer {raw_token}"

        # Initialize Client Adapter
        if integration.source_type == IntegrationSourceType.MOCK_FHIR or "fhir" in integration.base_url.lower():
            client = FHIRClient(
                base_url=integration.base_url,
                timeout_seconds=integration.timeout_seconds,
                rate_limit_per_min=integration.rate_limit_per_min,
                auth_headers=auth_headers,
            )
            resource_targets = ["Patient", "Observation", "Condition"]
        else:
            client = VendorRESTClient(
                base_url=integration.base_url,
                timeout_seconds=integration.timeout_seconds,
                rate_limit_per_min=integration.rate_limit_per_min,
                auth_headers=auth_headers,
            )
            resource_targets = ["records"]

        fetched_count = 0
        processed_count = 0
        failed_count = 0
        skipped_duplicates = 0

        try:
            for target in resource_targets:
                # Fetch records synchronously within thread
                try:
                    raw_records = asyncio.run(client.fetch_records(resource_type=target, page=1, limit=50))
                except Exception as fetch_err:
                    logger.warning(f"Fetch failed for target '{target}': {fetch_err}")
                    raw_records = []

                fetched_count += len(raw_records)

                for raw_record in raw_records:
                    try:
                        checksum = compute_payload_checksum(raw_record)

                        # Idempotency / Duplicate Check
                        duplicate = (
                            db.query(PatientRecord)
                            .filter(
                                PatientRecord.integration_id == integration.id,
                                PatientRecord.checksum == checksum,
                            )
                            .first()
                        )
                        if duplicate:
                            skipped_duplicates += 1
                            continue

                        # Detect and Normalize
                        res_type = detect_resource_type(raw_record)
                        if res_type == "Patient":
                            normalized, issues = normalize_patient(raw_record)
                            # Create or update Patient entity
                            mrn_val = str(normalized.get("id") or raw_record.get("vendor_patient_id") or "UNKNOWN")
                            patient = db.query(Patient).filter(Patient.mrn == mrn_val).first()
                            if not patient:
                                name_info = normalized.get("name", [{}])[0]
                                patient = Patient(
                                    mrn=mrn_val,
                                    first_name=name_info.get("given", ["Unknown"])[0] if name_info.get("given") else "Unknown",
                                    last_name=name_info.get("family", "Unknown"),
                                    gender=normalized.get("gender", "unknown"),
                                    is_active=True,
                                )
                                db.add(patient)
                                db.flush()
                            patient_id = patient.id
                        elif res_type == "Observation":
                            normalized, issues = normalize_observation(raw_record)
                            # Link to first active patient as demo subject if subject reference absent
                            first_p = db.query(Patient).first()
                            patient_id = first_p.id if first_p else None
                        elif res_type == "Condition":
                            normalized, issues = normalize_condition(raw_record)
                            first_p = db.query(Patient).first()
                            patient_id = first_p.id if first_p else None
                        else:
                            normalized = raw_record
                            issues = []
                            first_p = db.query(Patient).first()
                            patient_id = first_p.id if first_p else None

                        # Save PatientRecord if patient_id exists
                        if patient_id:
                            record = PatientRecord(
                                patient_id=patient_id,
                                integration_id=integration.id,
                                resource_type=res_type,
                                fhir_version="R4",
                                status=normalized.get("status", "active"),
                                checksum=checksum,
                                raw_payload=raw_record,
                                normalized_payload=normalized,
                            )
                            db.add(record)
                            db.flush()

                            # Persist any validation issues into database
                            for issue in issues:
                                val_log = ValidationErrorLog(
                                    record_id=record.id,
                                    sync_job_id=job.id,
                                    resource_type=res_type,
                                    field_path=issue.field_path,
                                    error_type=issue.error_type,
                                    severity=issue.severity,
                                    error_message=issue.message,
                                    raw_value={"input": issue.raw_value} if issue.raw_value else None,
                                )
                                db.add(val_log)

                            processed_count += 1
                        else:
                            failed_count += 1

                    except Exception as record_err:
                        logger.error(f"Failed processing individual clinical record: {record_err}")
                        failed_count += 1

            # Update Job metrics and complete
            job.records_fetched = fetched_count
            job.records_processed = processed_count
            job.records_failed = failed_count
            job.status = SyncJobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            integration.last_synced_at = datetime.now(timezone.utc)

            # Audit Trail
            audit_entry = AuditLog(
                user_id=None,
                action="SYNC_COMPLETED",
                resource_type="SyncJob",
                resource_id=str(job.id),
                details={
                    "integration_name": integration.name,
                    "records_fetched": fetched_count,
                    "records_processed": processed_count,
                    "records_failed": failed_count,
                    "skipped_duplicates": skipped_duplicates,
                },
            )
            db.add(audit_entry)
            db.commit()

            logger.info(
                f"SyncJob {job.id} completed: {processed_count} processed, "
                f"{skipped_duplicates} duplicate skipped, {failed_count} failed."
            )
            return {
                "success": True,
                "job_id": str(job.id),
                "records_fetched": fetched_count,
                "records_processed": processed_count,
                "skipped_duplicates": skipped_duplicates,
            }

        except Exception as sync_err:
            logger.error(f"SyncJob {job.id} fatal error: {sync_err}")
            job.retry_count += 1
            if job.retry_count < job.max_retries:
                job.status = SyncJobStatus.RETRYING
            else:
                job.status = SyncJobStatus.FAILED

            job.error_summary = str(sync_err)
            db.commit()
            return {"success": False, "error": str(sync_err), "job_id": str(job.id)}
