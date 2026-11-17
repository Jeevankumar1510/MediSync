from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid
from pydantic import BaseModel, Field, ConfigDict

from app.models.integration import (
    IntegrationSourceType,
    IntegrationAuthType,
    IntegrationStatus,
)


class IntegrationCredentialCreate(BaseModel):
    api_key: Optional[str] = Field(None, description="Plaintext API Key (will be encrypted with Fernet)")
    client_id: Optional[str] = Field(None, max_length=255)
    client_secret: Optional[str] = Field(None, description="Plaintext OAuth2 client secret (will be encrypted)")
    token_url: Optional[str] = Field(None, max_length=500)
    scopes: Optional[str] = Field(None, max_length=255)


class IntegrationCredentialResponse(BaseModel):
    id: uuid.UUID
    client_id: Optional[str] = None
    token_url: Optional[str] = None
    scopes: Optional[str] = None
    has_api_key: bool = False
    has_client_secret: bool = False
    has_access_token: bool = False
    token_expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class APIIntegrationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Unique human-readable integration identifier")
    description: Optional[str] = Field(None, max_length=500)
    source_type: IntegrationSourceType = Field(IntegrationSourceType.MOCK_FHIR, description="Connector source protocol")
    base_url: str = Field(..., max_length=500, description="Base API endpoint URL")
    auth_type: IntegrationAuthType = Field(IntegrationAuthType.NONE, description="Authentication mechanism")
    status: IntegrationStatus = Field(IntegrationStatus.ACTIVE, description="Current operational state")
    rate_limit_per_min: int = Field(60, ge=1, le=10000, description="Maximum API requests per minute")
    timeout_seconds: int = Field(30, ge=1, le=300, description="HTTP request timeout in seconds")
    config_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom provider parameters")


class APIIntegrationCreate(APIIntegrationBase):
    credentials: Optional[IntegrationCredentialCreate] = None


class APIIntegrationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    source_type: Optional[IntegrationSourceType] = None
    base_url: Optional[str] = None
    auth_type: Optional[IntegrationAuthType] = None
    status: Optional[IntegrationStatus] = None
    rate_limit_per_min: Optional[int] = Field(None, ge=1, le=10000)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    config_params: Optional[Dict[str, Any]] = None
    credentials: Optional[IntegrationCredentialCreate] = None


class APIIntegrationResponse(APIIntegrationBase):
    id: uuid.UUID
    last_synced_at: Optional[datetime] = None
    credential: Optional[IntegrationCredentialResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntegrationListResponse(BaseModel):
    items: List[APIIntegrationResponse]
    total: int


class ConnectionTestResult(BaseModel):
    success: bool
    status_code: Optional[int] = None
    latency_ms: float
    message: str
    details: Optional[Dict[str, Any]] = None


class SyncTriggerResponse(BaseModel):
    job_id: uuid.UUID
    integration_id: uuid.UUID
    status: str
    message: str
