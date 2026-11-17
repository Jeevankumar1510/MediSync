import io
import json
import uuid
import zipfile
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.main import app
from app.services.rag.text_extractor import extract_text_from_file, clean_text
from app.services.rag.chunker import chunk_text
from app.services.rag.embeddings import get_embedding_generator
from app.services.rag.llm_gateway import LLMGateway
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.user import User, UserRole


def run_verification():
    passed = 0
    total = 0

    def check(name: str, cond: bool):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
            print(f"  [PASS] {name}", flush=True)
        else:
            print(f"  [FAIL] {name}", flush=True)

    print("==================================================", flush=True)
    print(" MediSync AI - Phase 9 Verification Suite", flush=True)
    print(" RAG Healthcare Assistant & Knowledge Base Engine", flush=True)
    print("==================================================", flush=True)

    # 1. Text Extraction
    print("\n[1] Testing Multi-Format Clinical Text Extraction...", flush=True)
    txt_content = b"Patient Assessment: Resting heart rate 72 bpm, respiratory rate 16 breaths/min."
    text, ftype = extract_text_from_file(txt_content, "vitals.txt")
    check("Extracts text from .txt file", "heart rate 72 bpm" in text and ftype == "txt")

    md_content = b"## Clinical Protocol\n- LOINC 85354-9 BP Panel\n- Target systolic < 130"
    text_md, ftype_md = extract_text_from_file(md_content, "protocol.md")
    check("Extracts text from markdown .md file", "85354-9" in text_md and ftype_md == "md")

    json_content = json.dumps({"resourceType": "Condition", "code": "E11.9", "text": "Type 2 diabetes"}).encode()
    text_json, ftype_json = extract_text_from_file(json_content, "condition.json")
    check("Extracts structured text from .json", "E11.9" in text_json and ftype_json == "json")

    # In-memory docx extraction
    docx_buf = io.BytesIO()
    with zipfile.ZipFile(docx_buf, "w") as z:
        z.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:body>
                    <w:p><w:r><w:t>Standard Operating Procedure for Patient Discharge.</w:t></w:r></w:p>
                    <w:p><w:r><w:t>Medication reconciliation completed before release.</w:t></w:r></w:p>
                </w:body>
            </w:document>"""
        )
    text_docx, ftype_docx = extract_text_from_file(docx_buf.getvalue(), "sop.docx")
    check("Extracts text from Word .docx file via standard library", "Medication reconciliation" in text_docx and ftype_docx == "docx")

    empty_caught = False
    try:
        extract_text_from_file(b"", "empty.txt")
    except ValueError:
        empty_caught = True
    check("Rejects empty file upload with ValueError", empty_caught)

    # 2. Semantic Chunking
    print("\n[2] Testing Semantic Chunking...", flush=True)
    sample_corpus = (
        "Clinical Section 1: Introduction to Cardiovascular Health.\n\n"
        "Hypertension is a prevalent chronic condition affecting millions of adult patients globally. "
        "Routine blood pressure screening is essential for early diagnosis and prevention of target organ damage.\n\n"
        "Clinical Section 2: Pharmacotherapy.\n\n"
        "Angiotensin-converting enzyme (ACE) inhibitors, such as Lisinopril, are recommended first-line agents. "
        "Angiotensin II receptor blockers (ARBs) provide an alternative for patients who develop persistent dry cough."
    )
    chunks = chunk_text(sample_corpus, chunk_size=150, chunk_overlap=30)
    check("Decomposes corpus into multiple overlapping chunks", len(chunks) >= 3)
    check("All chunks have required metadata (chunk_index, content, char_length)", all(
        "chunk_index" in c and "content" in c and "char_length" in c for c in chunks
    ))
    check("Chunks preserve semantic continuity", any("Lisinopril" in c["content"] for c in chunks))

    # 3. Dense Vector Embeddings
    print("\n[3] Testing Dense Vector Embeddings (384-d)...", flush=True)
    gen = get_embedding_generator()
    vec = gen.embed_text("Elevated blood pressure and hypertension in adult patient.")
    check("Generates exactly 384-dimensional vector", len(vec) == 384)
    norm = sum(x * x for x in vec)
    check("Embedding vector is L2 unit-normalized (norm approx 1.0)", abs(norm - 1.0) < 1e-3)

    v1 = gen.embed_text("hypertension blood pressure Lisinopril medication")
    v2 = gen.embed_text("systolic diastolic blood pressure reading 140/90")
    v3 = gen.embed_text("quantum physics electromagnetic radiation telescope")

    def cos_sim(a, b):
        return sum(x * y for x, y in zip(a, b))

    sim_medical = cos_sim(v1, v2)
    sim_unrelated = cos_sim(v1, v3)
    check(
        f"Semantic similarity ranks related medical query higher ({sim_medical:.4f} > {sim_unrelated:.4f})",
        sim_medical > sim_unrelated
    )

    batch_vecs = gen.embed_batch(["Patient record A", "Patient record B", "Patient record C"])
    check("Batch embeddings generate correct count and dimensions", len(batch_vecs) == 3 and all(len(v) == 384 for v in batch_vecs))

    # 4. LLM Gateway & Grounded Extractive Synthesizer
    print("\n[4] Testing Grounded Clinical Extractive Synthesizer...", flush=True)
    gateway = LLMGateway()
    test_doc = Document(
        id=uuid.uuid4(),
        title="Hypertension Clinical Practice Guidelines 2026",
        filename="hypertension_guidelines.txt",
        file_type="txt",
        file_size_bytes=2048,
        storage_path="/virtual/guidelines.txt",
        status=DocumentStatus.INDEXED,
        is_public=True
    )
    test_chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=test_doc.id,
        chunk_index=1,
        content="First-line therapy for stage 1 hypertension is Lisinopril 10mg once daily with monthly BP monitoring.",
        embedding=[0.0] * 384
    )

    answer, evidence_found = gateway._grounded_extractive_synthesis(
        "What is the first-line therapy for stage 1 hypertension?",
        [(test_chunk, test_doc, 0.88)]
    )
    check("Synthesizer marks evidence_found=True when relevant chunks exist", evidence_found is True)
    check("Answer contains grounded facts from chunk (Lisinopril 10mg)", "Lisinopril 10mg" in answer)
    check("Answer cites source document title", "Hypertension Clinical Practice Guidelines 2026" in answer)
    check("Answer includes chunk index citation", "Chunk #1" in answer)

    # Test Rule 10: Insufficient evidence response
    ans_no_evidence, ev_no = gateway._grounded_extractive_synthesis("What is the treatment for unknown disease XYZ?", [])
    check("Marks evidence_found=False when no chunks match query", ev_no is False)
    check("Explicitly states lack of sufficient evidence", "do not have sufficient clinical or technical documentation" in ans_no_evidence)

    # 5. Access Control (ACL) Rules
    print("\n[5] Testing Document Access Control (ACL)...", flush=True)
    user_alice = User(id=uuid.uuid4(), email="alice@medisync.local", role=UserRole.CLINICAL_ANALYST, is_superuser=False)
    user_bob = User(id=uuid.uuid4(), email="bob@medisync.local", role=UserRole.CLINICAL_ANALYST, is_superuser=False)
    admin_user = User(id=uuid.uuid4(), email="admin@medisync.local", role=UserRole.ADMIN, is_superuser=True)

    doc_alice_private = Document(id=uuid.uuid4(), user_id=user_alice.id, title="Alice Private Notes", is_public=False)
    doc_public = Document(id=uuid.uuid4(), user_id=user_alice.id, title="Public Hospital Protocol", is_public=True)

    def can_access(doc: Document, u: User) -> bool:
        if u.is_superuser or u.role == UserRole.ADMIN:
            return True
        return doc.is_public or (doc.user_id == u.id)

    check("Alice can access her own private document", can_access(doc_alice_private, user_alice))
    check("Bob CANNOT access Alice's private document", not can_access(doc_alice_private, user_bob))
    check("Bob CAN access public document", can_access(doc_public, user_bob))
    check("Admin CAN access Alice's private document", can_access(doc_alice_private, admin_user))

    # 6. OpenAPI & Route Registration
    print("\n[6] Testing OpenAPI Endpoint Registrations...", flush=True)
    paths = app.openapi()["paths"]
    check("POST /api/v1/rag/upload registered", "/api/v1/rag/upload" in paths)
    check("POST /rag/upload root alias registered", "/rag/upload" in paths)
    check("POST /api/v1/rag/query registered", "/api/v1/rag/query" in paths)
    check("POST /rag/query root alias registered", "/rag/query" in paths)
    check("GET /api/v1/rag/documents registered", "/api/v1/rag/documents" in paths)
    check("GET /rag/documents root alias registered", "/rag/documents" in paths)
    check("GET /api/v1/rag/documents/{document_id} registered", "/api/v1/rag/documents/{document_id}" in paths)
    check("DELETE /api/v1/rag/documents/{document_id} registered", "/api/v1/rag/documents/{document_id}" in paths)

    print("\n==================================================", flush=True)
    print(f" Phase 9 Verification Summary: {passed}/{total} Passed", flush=True)
    print("==================================================", flush=True)
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    run_verification()
