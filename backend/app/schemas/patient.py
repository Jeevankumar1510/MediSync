from datetime import date, datetime
from typing import Dict, List, Optional, Any
import uuid
from pydantic import BaseModel, Field, ConfigDict


class ContactInfo(BaseModel):
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    emergency_contact: Optional[str] = Field(None, max_length=255)


class Address(BaseModel):
    line: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field("USA", max_length=100)


class PatientBase(BaseModel):
    mrn: str = Field(..., min_length=3, max_length=100, description="Medical Record Number (Unique Identifier)")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    birth_date: Optional[date] = None
    gender: Optional[str] = Field("unknown", description="male, female, other, unknown")
    contact_info: Optional[Dict[str, Any]] = Field(default_factory=dict)
    address: Optional[Dict[str, Any]] = Field(default_factory=dict)
    is_active: bool = True


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    contact_info: Optional[Dict[str, Any]] = None
    address: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class PatientResponse(PatientBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    records_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class PatientListResponse(BaseModel):
    items: List[PatientResponse]
    total: int
    page: int
    size: int
    pages: int


# Patient Clinical Records (FHIR Normalized Resources)
class PatientRecordBase(BaseModel):
    resource_type: str = Field(..., min_length=2, max_length=50, description="FHIR resourceType (e.g. Observation, Condition, Encounter)")
    fhir_version: str = Field("R4", max_length=10)
    status: str = Field("active", max_length=50)
    raw_payload: Dict[str, Any] = Field(..., description="Original raw incoming payload")
    normalized_payload: Optional[Dict[str, Any]] = Field(None, description="FHIR-compliant normalized structure")


class PatientRecordCreate(PatientRecordBase):
    provider_id: Optional[uuid.UUID] = None
    integration_id: Optional[uuid.UUID] = None


class PatientRecordResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: Optional[uuid.UUID] = None
    integration_id: Optional[uuid.UUID] = None
    resource_type: str
    fhir_version: str
    status: str
    checksum: Optional[str] = None
    raw_payload: Dict[str, Any]
    normalized_payload: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
