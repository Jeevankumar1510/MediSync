"""
Seed synthetic clinical practice guidelines, FHIR R4 manuals, and hospital SOPs
into the MediSync AI Knowledge Base with 384-d dense vector embeddings.
Run with: python seed_documents.py
"""
import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database import get_sync_db
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.user import User
from app.services.rag.chunker import chunk_text
from app.services.rag.embeddings import get_embedding_generator

KNOWLEDGE_DOCUMENTS = [
    {
        "title": "Cardiovascular Clinical Practice Guidelines 2026",
        "filename": "cardiovascular_guidelines_2026.md",
        "file_type": "md",
        "is_public": True,
        "content": (
            "# Cardiovascular Clinical Practice Guidelines 2026\n\n"
            "## 1. Classification of Blood Pressure in Adults\n"
            "- Normal Blood Pressure: Systolic < 120 mmHg and Diastolic < 80 mmHg.\n"
            "- Elevated Blood Pressure: Systolic 120-129 mmHg and Diastolic < 80 mmHg.\n"
            "- Stage 1 Hypertension: Systolic 130-139 mmHg or Diastolic 80-89 mmHg.\n"
            "- Stage 2 Hypertension: Systolic >= 140 mmHg or Diastolic >= 90 mmHg.\n"
            "- Hypertensive Crisis: Systolic > 180 mmHg and/or Diastolic > 120 mmHg.\n\n"
            "## 2. Pharmacological Management\n"
            "First-line pharmacological therapy for non-black patients with Stage 1 or Stage 2 hypertension "
            "includes thiazide diuretics, calcium channel blockers (CCBs such as Amlodipine 5-10mg daily), "
            "or ACE inhibitors (such as Lisinopril 10-40mg once daily). "
            "For patients experiencing dry cough with ACE inhibitors, Angiotensin Receptor Blockers (ARBs such as Losartan) "
            "are the recommended alternative. Renal function and serum potassium must be evaluated within 2 to 4 weeks "
            "of initiating ACE inhibitor therapy.\n\n"
            "## 3. Lifestyle Modifications\n"
            "Non-pharmacological interventions include dietary sodium reduction (< 1500 mg/day), adherence to the DASH diet, "
            "regular aerobic physical activity (at least 150 minutes per week), and alcohol moderation."
        )
    },
    {
        "title": "HL7 FHIR R4 Clinical Integration Specification",
        "filename": "fhir_r4_integration_spec.md",
        "file_type": "md",
        "is_public": True,
        "content": (
            "# HL7 FHIR R4 Clinical Integration Specification\n\n"
            "## 1. Patient Resource Guidelines\n"
            "Every ingested patient must include a canonical Medical Record Number (MRN) mapped to identifier[0].value. "
            "Demographics require given name, family name, birthDate in ISO-8601 format (YYYY-MM-DD), and standard gender codes "
            "(male, female, other, unknown).\n\n"
            "## 2. Observation Resource & Vital Signs Panel\n"
            "Blood pressure measurements must adhere to LOINC code 85354-9 (Blood pressure panel with all children optional). "
            "The panel is decomposed into two constituent components: "
            "1. Systolic blood pressure: LOINC 8480-6 with UCUM unit 'mmHg'.\n"
            "2. Diastolic blood pressure: LOINC 8462-4 with UCUM unit 'mmHg'.\n"
            "Heart rate observations must use LOINC 8867-4 with unit '/min'. Body temperature utilizes LOINC 8310-5 (Cel).\n\n"
            "## 3. Condition Resource & Diagnostic Coding\n"
            "Clinical diagnoses and problems must be cataloged under the Condition resource, utilizing ICD-10-CM coding systems. "
            "Examples include E11.9 for Type 2 diabetes mellitus without complications and I10 for Essential primary hypertension."
        )
    },
    {
        "title": "MediSync AI Data Governance & HIPAA Audit Policy",
        "filename": "data_governance_policy.txt",
        "file_type": "txt",
        "is_public": True,
        "content": (
            "MediSync AI Data Governance and Compliance Standard Operating Procedure:\n\n"
            "1. Immutable Audit Logging:\n"
            "Every patient access, clinical record modification, data synchronization job, and AI inference query "
            "is logged immutably to the audit_logs table. Audit records capture user_id, action, resource_type, "
            "resource_id, timestamp, and context details.\n\n"
            "2. Webhook Integrity & HMAC Authentication:\n"
            "All inbound EHR webhooks must supply an HMAC-SHA256 signature in the X-MediSync-Signature header. "
            "Payloads with missing or mismatched signatures are rejected immediately with HTTP 401 Unauthorized.\n\n"
            "3. AI Safety & Non-Mutation Rule:\n"
            "The AI Anomaly Detection and Clinical Assistant modules provide observational quality insights and grounded RAG responses. "
            "Under no circumstances does an AI model or heuristic algorithm alter, mutate, or overwrite primary clinical records."
        )
    }
]


def seed_documents():
    embed_gen = get_embedding_generator()

    with get_sync_db() as db:
        # Fetch an admin user to assign as uploader
        admin = db.query(User).filter(User.email == "admin@medisync.local").first()
        if not admin:
            admin = db.query(User).first()
        if not admin:
            print("No user found to associate documents. Please run seed_users.py first.")
            return

        print(f"Seeding knowledge base documents as user: {admin.email}...")

        for doc_data in KNOWLEDGE_DOCUMENTS:
            existing = db.query(Document).filter(Document.title == doc_data["title"]).first()
            if existing:
                print(f"  [EXISTS] Document '{doc_data['title']}' already indexed ({existing.chunk_count} chunks).")
                continue

            doc_id = uuid.uuid4()
            raw_text = doc_data["content"].strip()
            file_bytes = raw_text.encode("utf-8")

            # Chunk text
            chunks = chunk_text(raw_text, chunk_size=400, chunk_overlap=40)
            chunk_contents = [c["content"] for c in chunks]
            embeddings = embed_gen.embed_batch(chunk_contents)

            doc = Document(
                id=doc_id,
                user_id=admin.id,
                title=doc_data["title"],
                filename=doc_data["filename"],
                file_type=doc_data["file_type"],
                file_size_bytes=len(file_bytes),
                storage_path=f"storage/documents/{doc_data['filename']}",
                status=DocumentStatus.INDEXED,
                is_public=doc_data["is_public"],
                chunk_count=len(chunks)
            )
            db.add(doc)
            db.flush()

            for c_data, emb in zip(chunks, embeddings):
                chunk_obj = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=c_data["chunk_index"],
                    content=c_data["content"],
                    embedding=emb,
                    chunk_metadata={
                        "char_length": c_data["char_length"],
                        "file_type": doc_data["file_type"]
                    }
                )
                db.add(chunk_obj)

            db.commit()
            print(f"  [CREATED] Indexed '{doc.title}' ({len(chunks)} chunks with 384-d vectors).")

        print("Knowledge base documents seeded successfully.")


if __name__ == "__main__":
    seed_documents()
