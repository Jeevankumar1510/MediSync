import uuid
import pytest
from pydantic import ValidationError

from app.core.encryption import encrypt_secret, decrypt_secret
from app.models.integration import (
    IntegrationSourceType,
    IntegrationAuthType,
    IntegrationStatus,
)
from app.schemas.integration import (
    APIIntegrationCreate,
    IntegrationCredentialCreate,
    IntegrationCredentialResponse,
)
from app.main import app


def test_fernet_encryption_roundtrip():
    """Verify that sensitive secrets are encrypted and decrypted without data loss."""
    raw_secret = "epic_ehr_client_secret_998877_live"
    encrypted = encrypt_secret(raw_secret)
    assert encrypted is not None
    assert encrypted != raw_secret
    assert not encrypted.startswith("epic_")

    decrypted = decrypt_secret(encrypted)
    assert decrypted == raw_secret


def test_encryption_handles_none_safely():
    """Verify that None/empty values do not crash encryption."""
    assert encrypt_secret(None) is None
    assert decrypt_secret(None) is None


def test_integration_create_schema_validation():
    """Verify constraints on rate limits and timeouts."""
    # Fails if rate_limit_per_min < 1
    with pytest.raises(ValidationError):
        APIIntegrationCreate(
            name="FHIR Gateway",
            base_url="https://fhir.example.com",
            rate_limit_per_min=0,
        )

    # Valid schema with credentials
    valid = APIIntegrationCreate(
        name="Cerner Millenium FHIR",
        base_url="https://cerner-fhir.hospital.org/r4",
        source_type=IntegrationSourceType.MOCK_FHIR,
        auth_type=IntegrationAuthType.BEARER_TOKEN,
        rate_limit_per_min=100,
        timeout_seconds=20,
        credentials=IntegrationCredentialCreate(
            client_id="client_cerner_01",
            api_key="secret_key_123",
        )
    )
    assert valid.name == "Cerner Millenium FHIR"
    assert valid.rate_limit_per_min == 100


def test_credential_response_masks_secrets():
    """Verify that response models redact raw secrets and only expose presence flags."""
    cred_resp = IntegrationCredentialResponse(
        id=uuid.uuid4(),
        client_id="client_abc",
        has_api_key=True,
        has_client_secret=True,
    )
    dumped = cred_resp.model_dump()
    assert dumped["has_api_key"] is True
    assert dumped["has_client_secret"] is True
    assert "api_key" not in dumped
    assert "client_secret" not in dumped


def test_integration_and_mock_routes_registered():
    """Verify that all required API integration and mock EHR endpoints are registered."""
    paths = app.openapi()["paths"]

    # API v1 endpoints
    assert "/api/v1/integrations" in paths
    assert "get" in paths["/api/v1/integrations"]
    assert "post" in paths["/api/v1/integrations"]

    assert "/api/v1/integrations/{integration_id}" in paths
    assert "get" in paths["/api/v1/integrations/{integration_id}"]
    assert "put" in paths["/api/v1/integrations/{integration_id}"]
    assert "delete" in paths["/api/v1/integrations/{integration_id}"]

    assert "/api/v1/integrations/{integration_id}/test-connection" in paths
    assert "/api/v1/integrations/{integration_id}/sync" in paths

    # Root aliases (required by Section 5)
    assert "/integrations" in paths
    assert "/integrations/{integration_id}/sync" in paths

    # Mock EHR services
    assert "/mock-fhir/metadata" in paths
    assert "/mock-fhir/Patient" in paths
    assert "/mock-fhir/Observation" in paths
    assert "/mock-fhir/Condition" in paths
    assert "/mock-vendor/records" in paths
