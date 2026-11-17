import json
import pytest

from app.core.webhook_security import verify_hmac_signature, generate_hmac_signature
from app.schemas.webhook import WebhookEventIngest, WebhookIngestResponse
from app.main import app


def test_hmac_signature_verification():
    """Verify HMAC-SHA256 signature generation and constant-time validation."""
    secret = "whsec_healthcare_partner_test_key_998877"
    raw_payload = json.dumps({"event": "patient.create", "id": "12345"}).encode("utf-8")

    valid_sig = generate_hmac_signature(raw_payload, secret)

    # 1. Exact raw signature
    assert verify_hmac_signature(raw_payload, valid_sig, secret) is True

    # 2. Prefixed sha256= signature (GitHub/Stripe/Epic format)
    assert verify_hmac_signature(raw_payload, f"sha256={valid_sig}", secret) is True

    # 3. Tampered payload fails
    tampered = json.dumps({"event": "patient.create", "id": "12346"}).encode("utf-8")
    assert verify_hmac_signature(tampered, valid_sig, secret) is False

    # 4. Wrong secret fails
    assert verify_hmac_signature(raw_payload, valid_sig, "wrong_secret_key") is False


def test_webhook_schema_validation():
    """Verify WebhookEventIngest schema constraints."""
    event = WebhookEventIngest(
        source="Epic",
        event_type="patient.create",
        event_id="evt_epic_9988",
        payload={"mrn": "MRN-WEBHOOK-01", "name": "Test Patient"},
    )
    assert event.source == "Epic"
    assert event.event_type == "patient.create"
    assert event.event_id == "evt_epic_9988"


def test_webhook_openapi_routes_registered():
    """Verify all webhook ingestion, monitoring, and retry endpoints are active in OpenAPI schema."""
    paths = app.openapi()["paths"]

    # API v1 endpoints
    assert "/api/v1/webhooks/events" in paths
    assert "post" in paths["/api/v1/webhooks/events"]
    assert "get" in paths["/api/v1/webhooks/events"]
    assert "/api/v1/webhooks/events/{event_id}/retry" in paths
    assert "post" in paths["/api/v1/webhooks/events/{event_id}/retry"]

    # Root aliases (required by Section 5)
    assert "/webhooks/events" in paths
    assert "/webhooks/events/{event_id}/retry" in paths
