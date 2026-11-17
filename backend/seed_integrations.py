"""
Seed pre-configured demo healthcare integrations with encrypted credentials.
Run with: python seed_integrations.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database import get_sync_db
from app.models.integration import (
    APIIntegration,
    IntegrationCredential,
    IntegrationSourceType,
    IntegrationAuthType,
    IntegrationStatus,
)
from app.core.encryption import encrypt_secret

DEMO_INTEGRATIONS = [
    {
        "name": "Synthea Public Mock FHIR Gateway",
        "description": "Synthetic FHIR R4 Bundle repository simulating outpatient EHR records.",
        "source_type": IntegrationSourceType.MOCK_FHIR,
        "base_url": "http://localhost:8000/mock-fhir",
        "auth_type": IntegrationAuthType.BEARER_TOKEN,
        "status": IntegrationStatus.ACTIVE,
        "rate_limit_per_min": 120,
        "timeout_seconds": 15,
        "credentials": {
            "api_key": None,
            "access_token": "synthea_demo_mock_bearer_token_xyz987",
            "client_id": "synthea-client-app-01",
        }
    },
    {
        "name": "Memorial Hospital Vendor EHR",
        "description": "Legacy non-standard EHR REST pipeline exporting un-normalized clinical payloads.",
        "source_type": IntegrationSourceType.REST_JSON,
        "base_url": "http://localhost:8000/mock-vendor",
        "auth_type": IntegrationAuthType.API_KEY,
        "status": IntegrationStatus.ACTIVE,
        "rate_limit_per_min": 60,
        "timeout_seconds": 30,
        "credentials": {
            "api_key": "ehr_vendor_live_api_key_44332211",
            "access_token": None,
            "client_id": "vendor-gateway-memorial",
        }
    }
]


def seed_integrations():
    print("Seeding demo healthcare integrations...")
    with get_sync_db() as db:
        for item in DEMO_INTEGRATIONS:
            existing = db.query(APIIntegration).filter(APIIntegration.name == item["name"]).first()
            if existing:
                print(f"[-] Integration already exists: {item['name']}")
                continue

            integ = APIIntegration(
                name=item["name"],
                description=item["description"],
                source_type=item["source_type"],
                base_url=item["base_url"],
                auth_type=item["auth_type"],
                status=item["status"],
                rate_limit_per_min=item["rate_limit_per_min"],
                timeout_seconds=item["timeout_seconds"],
                config_params={"auto_retry": True, "backoff_factor": 1.5}
            )
            db.add(integ)
            db.flush()

            # Encrypt and store credentials
            c_data = item["credentials"]
            cred = IntegrationCredential(
                integration_id=integ.id,
                encrypted_api_key=encrypt_secret(c_data["api_key"]) if c_data["api_key"] else None,
                encrypted_access_token=encrypt_secret(c_data["access_token"]) if c_data["access_token"] else None,
                client_id=c_data["client_id"],
            )
            db.add(cred)
            print(f"[+] Created Integration: {integ.name} (Source: {integ.source_type.value}, Vaulted: YES)")

        db.commit()
    print("Integration seeding completed successfully!")


if __name__ == "__main__":
    seed_integrations()
