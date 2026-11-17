from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid
from pydantic import BaseModel, Field, ConfigDict

from app.models.webhook import WebhookStatus


class WebhookEventIngest(BaseModel):
    source: str = Field(..., min_length=2, max_length=100, description="Originating system (e.g. Epic, Cerner, Synthea)")
    event_type: str = Field(..., min_length=2, max_length=100, description="e.g. patient.create, observation.updated, condition.diagnosed")
    event_id: Optional[str] = Field(None, max_length=255, description="External unique event identifier for idempotency")
    integration_id: Optional[uuid.UUID] = Field(None, description="Optional registered APIIntegration UUID")
    payload: Dict[str, Any] = Field(..., description="Clinical JSON payload")


class WebhookIngestResponse(BaseModel):
    event_id: str
    status: str
    message: str
    idempotent_duplicate: bool = False


class WebhookEventResponse(BaseModel):
    id: uuid.UUID
    integration_id: Optional[uuid.UUID] = None
    event_id: Optional[str] = None
    source: str
    event_type: str
    status: str
    error_message: Optional[str] = None
    retry_count: int = 0
    payload: Dict[str, Any]
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class WebhookEventListResponse(BaseModel):
    items: List[WebhookEventResponse]
    total: int
    page: int
    size: int
