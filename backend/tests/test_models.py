import uuid
from app.models import (
    Base,
    User,
    UserRole,
    HealthcareProvider,
    APIIntegration,
    IntegrationCredential,
    IntegrationSourceType,
    IntegrationAuthType,
    IntegrationStatus,
    Patient,
    PatientRecord,
    SyncJob,
    SyncJobStatus,
    WebhookEvent,
    ValidationErrorLog,
    Document,
    DocumentChunk,
    AIAnalysis,
    Conversation,
    ChatMessage,
    AuditLog,
)


def test_models_metadata_registered():
    """Verify that all core tables are mapped in SQLAlchemy metadata."""
    table_names = Base.metadata.tables.keys()
    expected_tables = [
        "users",
        "healthcare_providers",
        "api_integrations",
        "integration_credentials",
        "patients",
        "patient_records",
        "synchronization_jobs",
        "webhook_events",
        "validation_error_logs",
        "documents",
        "document_chunks",
        "ai_analyses",
        "conversations",
        "chat_messages",
        "audit_logs",
    ]
    for table in expected_tables:
        assert table in table_names, f"Table '{table}' missing from Base.metadata"


def test_user_instantiation():
    user = User(
        email="doctor@medisync.local",
        hashed_password="secure_hash_here",
        full_name="Dr. Alex Rivera",
        role=UserRole.CLINICAL_ANALYST,
        is_active=True,
    )
    assert user.email == "doctor@medisync.local"
    assert user.role == UserRole.CLINICAL_ANALYST
    assert user.is_active is True


def test_patient_and_record_instantiation():
    patient = Patient(
        mrn="MRN-100234",
        first_name="Jane",
        last_name="Doe",
    )
    record = PatientRecord(
        patient_id=patient.id,
        resource_type="Observation",
        raw_payload={"type": "vitals", "bp": "120/80"},
        normalized_payload={"resourceType": "Observation", "status": "final"},
    )
    assert patient.mrn == "MRN-100234"
    assert record.resource_type == "Observation"
    assert record.normalized_payload["resourceType"] == "Observation"

