from datetime import date
from typing import Dict, List, Literal, Optional, Any, Union
import re
from pydantic import BaseModel, Field, field_validator, ConfigDict


class FHIRCoding(BaseModel):
    system: Optional[str] = Field(None, description="Identity of the terminology system (e.g. http://loinc.org)")
    code: str = Field(..., description="Symbol in syntax defined by the system")
    display: Optional[str] = Field(None, description="Representation defined by the system")


class FHIRCodeableConcept(BaseModel):
    coding: List[FHIRCoding] = Field(default_factory=list, description="Code defined by a terminology system")
    text: Optional[str] = Field(None, description="Plain text representation of the concept")


class FHIRQuantity(BaseModel):
    value: float = Field(..., description="Numerical value")
    unit: Optional[str] = Field(None, description="Unit representation (e.g. mmHg, mg/dL, /min)")
    system: Optional[str] = Field(None, description="System that defines coded unit form (e.g. http://unitsofmeasure.org)")
    code: Optional[str] = Field(None, description="Coded form of the unit")


class FHIRIdentifier(BaseModel):
    system: Optional[str] = Field(None, description="The namespace for the identifier value")
    value: str = Field(..., description="The value that is unique within the namespace")
    use: Optional[str] = Field("usual", description="usual | official | temp | secondary | old")


class FHIRHumanName(BaseModel):
    use: Optional[str] = Field("official", description="usual | official | temp | nickname | anonymous | old | maiden")
    family: Optional[str] = Field(None, description="Family name (often called 'Surname')")
    given: Optional[List[str]] = Field(default_factory=list, description="Given names (not always 'first'). Includes middle names")
    text: Optional[str] = Field(None, description="Text representation of the full name")


class FHIRReference(BaseModel):
    reference: str = Field(..., description="Literal reference, Relative, internal or absolute URL")
    display: Optional[str] = Field(None, description="Text alternative for the resource")


# Core FHIR R4 Resources
class FHIRPatientResource(BaseModel):
    resourceType: Literal["Patient"] = "Patient"
    id: Optional[str] = None
    identifier: List[FHIRIdentifier] = Field(default_factory=list)
    active: bool = True
    name: List[FHIRHumanName] = Field(default_factory=list)
    gender: Optional[str] = Field(None, description="male | female | other | unknown")
    birthDate: Optional[Union[date, str]] = None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.lower().strip()
            if clean not in ["male", "female", "other", "unknown"]:
                raise ValueError(f"Invalid FHIR administrative gender '{v}'. Must be male, female, other, or unknown.")
            return clean
        return None

    @field_validator("birthDate")
    @classmethod
    def validate_birthdate_format(cls, v: Optional[Union[date, str]]) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, date):
            return v.isoformat()
        # Ensure YYYY-MM-DD format
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(v).strip()):
            raise ValueError(f"BirthDate '{v}' must adhere to standard YYYY-MM-DD ISO format.")
        return str(v).strip()

    model_config = ConfigDict(extra="allow")


class FHIRObservationResource(BaseModel):
    resourceType: Literal["Observation"] = "Observation"
    id: Optional[str] = None
    status: str = Field("final", description="registered | preliminary | final | amended | corrected | cancelled | entered-in-error | unknown")
    category: Optional[List[FHIRCodeableConcept]] = None
    code: FHIRCodeableConcept
    subject: Optional[FHIRReference] = None
    effectiveDateTime: Optional[str] = None
    valueQuantity: Optional[FHIRQuantity] = None
    component: Optional[List[Dict[str, Any]]] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = [
            "registered", "preliminary", "final", "amended",
            "corrected", "cancelled", "entered-in-error", "unknown"
        ]
        clean = v.lower().strip()
        if clean not in valid_statuses:
            raise ValueError(f"Invalid FHIR Observation status '{v}'. Must be one of {valid_statuses}")
        return clean

    model_config = ConfigDict(extra="allow")


class FHIRConditionResource(BaseModel):
    resourceType: Literal["Condition"] = "Condition"
    id: Optional[str] = None
    clinicalStatus: Optional[FHIRCodeableConcept] = None
    verificationStatus: Optional[FHIRCodeableConcept] = None
    category: Optional[List[FHIRCodeableConcept]] = None
    code: FHIRCodeableConcept
    subject: Optional[FHIRReference] = None
    onsetDateTime: Optional[str] = None

    model_config = ConfigDict(extra="allow")
