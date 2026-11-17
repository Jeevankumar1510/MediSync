"""
Seed synthetic demo patients and FHIR-compatible clinical records.
Run with: python seed_patients.py
"""
import sys
import os
from datetime import date
import hashlib
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database import get_sync_db
from app.models.patient import Patient, PatientRecord
from app.models.provider import HealthcareProvider


def compute_checksum(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


DEMO_PATIENTS = [
    {
        "mrn": "MRN-100201",
        "first_name": "Jane",
        "last_name": "Doe",
        "birth_date": date(1985, 4, 12),
        "gender": "female",
        "contact_info": {"phone": "555-0101", "email": "jane.doe@example.com"},
        "address": {"city": "Boston", "state": "MA", "postal_code": "02115", "country": "USA"},
        "records": [
            {
                "resource_type": "Observation",
                "status": "final",
                "raw_payload": {
                    "vendor": "Synthea",
                    "code": "85354-9",
                    "display": "Blood Pressure",
                    "systolic": 128,
                    "diastolic": 82,
                    "unit": "mmHg"
                },
                "normalized_payload": {
                    "resourceType": "Observation",
                    "status": "final",
                    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
                    "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood Pressure"}]},
                    "component": [
                        {"code": {"coding": [{"code": "8480-6", "display": "Systolic"}]}, "valueQuantity": {"value": 128, "unit": "mmHg"}},
                        {"code": {"coding": [{"code": "8462-4", "display": "Diastolic"}]}, "valueQuantity": {"value": 82, "unit": "mmHg"}}
                    ]
                }
            },
            {
                "resource_type": "Condition",
                "status": "active",
                "raw_payload": {"diagnosis": "Essential Hypertension", "icd10": "I10", "onset": "2021-03-15"},
                "normalized_payload": {
                    "resourceType": "Condition",
                    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                    "code": {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10", "code": "I10", "display": "Essential Hypertension"}]}
                }
            }
        ]
    },
    {
        "mrn": "MRN-100202",
        "first_name": "John",
        "last_name": "Miller",
        "birth_date": date(1972, 9, 23),
        "gender": "male",
        "contact_info": {"phone": "555-0102", "email": "john.miller@example.com"},
        "address": {"city": "Cambridge", "state": "MA", "postal_code": "02138", "country": "USA"},
        "records": [
            {
                "resource_type": "Observation",
                "status": "final",
                "raw_payload": {"test": "Fasting Blood Glucose", "value": 115, "unit": "mg/dL"},
                "normalized_payload": {
                    "resourceType": "Observation",
                    "status": "final",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "1558-6", "display": "Fasting Glucose [Mass/volume] in Serum or Plasma"}]},
                    "valueQuantity": {"value": 115, "unit": "mg/dL", "system": "http://unitsofmeasure.org"}
                }
            }
        ]
    },
    {
        "mrn": "MRN-100203",
        "first_name": "Sofia",
        "last_name": "Rodriguez",
        "birth_date": date(1994, 11, 30),
        "gender": "female",
        "contact_info": {"phone": "555-0103", "email": "sofia.r@example.com"},
        "address": {"city": "Somerville", "state": "MA", "postal_code": "02143", "country": "USA"},
        "records": [
            {
                "resource_type": "Observation",
                "status": "final",
                "raw_payload": {"metric": "Heart Rate", "bpm": 72},
                "normalized_payload": {
                    "resourceType": "Observation",
                    "status": "final",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
                    "valueQuantity": {"value": 72, "unit": "/min"}
                }
            }
        ]
    }
]


def seed_patients():
    print("Seeding synthetic demo patients...")
    with get_sync_db() as db:
        # Create a sample hospital provider if not exists
        provider = db.query(HealthcareProvider).filter(HealthcareProvider.npi == "NPI-9988776655").first()
        if not provider:
            provider = HealthcareProvider(
                name="Massachusetts General Memorial Hospital",
                npi="NPI-9988776655",
                organization_type="HOSPITAL",
                contact_email="records@massgeneral-demo.org",
                phone="555-0199",
                address={"city": "Boston", "state": "MA", "country": "USA"}
            )
            db.add(provider)
            db.flush()
            print(f"[+] Created Healthcare Provider: {provider.name}")

        for p_data in DEMO_PATIENTS:
            existing = db.query(Patient).filter(Patient.mrn == p_data["mrn"]).first()
            if existing:
                print(f"[-] Patient already exists: {p_data['mrn']}")
                continue

            patient = Patient(
                mrn=p_data["mrn"],
                first_name=p_data["first_name"],
                last_name=p_data["last_name"],
                birth_date=p_data["birth_date"],
                gender=p_data["gender"],
                contact_info=p_data["contact_info"],
                address=p_data["address"],
                is_active=True
            )
            db.add(patient)
            db.flush()
            print(f"[+] Created Patient: {patient.mrn} ({patient.first_name} {patient.last_name})")

            # Attach clinical records
            for r_data in p_data["records"]:
                record = PatientRecord(
                    patient_id=patient.id,
                    provider_id=provider.id,
                    resource_type=r_data["resource_type"],
                    fhir_version="R4",
                    status=r_data["status"],
                    checksum=compute_checksum(r_data["raw_payload"]),
                    raw_payload=r_data["raw_payload"],
                    normalized_payload=r_data["normalized_payload"]
                )
                db.add(record)
                print(f"    -> Added FHIR {record.resource_type} record")

        db.commit()
    print("Patient seeding completed successfully!")


if __name__ == "__main__":
    seed_patients()
