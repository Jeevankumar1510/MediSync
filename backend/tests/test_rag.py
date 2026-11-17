import io
import json
import zipfile
import pytest

from app.main import app
from app.services.rag.text_extractor import extract_text_from_file, clean_text
from app.services.rag.chunker import chunk_text
from app.services.rag.embeddings import get_embedding_generator
from app.services.rag.llm_gateway import LLMGateway
from app.models.document import Document, DocumentChunk, DocumentStatus


def test_rag_endpoints_registered_in_openapi():
    """Verify all RAG endpoints are registered under both /api/v1/rag and /rag in OpenAPI schema."""
    paths = app.openapi()["paths"]
    
    # Check v1 routes
    assert "/api/v1/rag/upload" in paths
    assert "/api/v1/rag/query" in paths
    assert "/api/v1/rag/documents" in paths
    assert "/api/v1/rag/documents/{document_id}" in paths

    # Check root alias routes
    assert "/rag/upload" in paths
    assert "/rag/query" in paths
    assert "/rag/documents" in paths
    assert "/rag/documents/{document_id}" in paths


def test_text_extractor_txt_and_md():
    """Test plain text and markdown extraction."""
    raw = b"Clinical Summary:\n\nPatient presented with acute bronchitis.\nPrescribed Amoxicillin."
    text, ftype = extract_text_from_file(raw, "summary.txt")
    assert ftype == "txt"
    assert "bronchitis" in text
    assert "Amoxicillin" in text

    md_raw = b"# FHIR Protocol\n\n- Observation 85354-9\n- Systolic BP"
    md_text, md_ftype = extract_text_from_file(md_raw, "fhir.md")
    assert md_ftype == "md"
    assert "Observation" in md_text


def test_text_extractor_json():
    """Test JSON structured extraction."""
    data = {"resourceType": "Observation", "code": "85354-9", "value": 120}
    raw = json.dumps(data).encode("utf-8")
    text, ftype = extract_text_from_file(raw, "obs.json")
    assert ftype == "json"
    parsed = json.loads(text)
    assert parsed["resourceType"] == "Observation"


def test_text_extractor_docx_in_memory():
    """Test docx extraction using in-memory zipfile and XML (no paid dependencies)."""
    docx_buffer = io.BytesIO()
    with zipfile.ZipFile(docx_buffer, "w") as z:
        z.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:body>
                    <w:p><w:r><w:t>Clinical Guidelines for Type 2 Diabetes.</w:t></w:r></w:p>
                    <w:p><w:r><w:t>Target HbA1c is below 7.0 percent.</w:t></w:r></w:p>
                </w:body>
            </w:document>"""
        )
    raw_docx = docx_buffer.getvalue()
    text, ftype = extract_text_from_file(raw_docx, "guidelines.docx")
    assert ftype == "docx"
    assert "Type 2 Diabetes" in text
    assert "HbA1c" in text


def test_text_extractor_empty_file():
    """Verify empty files raise ValueError."""
    with pytest.raises(ValueError, match="File content is empty"):
        extract_text_from_file(b"", "empty.txt")


def test_chunker_basic():
    """Test semantic text chunking."""
    text = (
        "Clinical Protocol A.\n\n"
        "Hypertension management requires daily blood pressure tracking.\n"
        "Patients with systolic blood pressure exceeding 140 mmHg require therapeutic intervention.\n\n"
        "First line agents include ACE inhibitors such as Lisinopril."
    )
    chunks = chunk_text(text, chunk_size=120, chunk_overlap=20)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c["content"]) <= 140
        assert "content" in c
        assert "chunk_index" in c


def test_chunker_short_text():
    """Verify single chunk returned for text shorter than chunk_size."""
    text = "Short clinical observation."
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["content"] == text


def test_embeddings_dimension_and_norm():
    """Verify embeddings produce 384 dimensions and unit norm."""
    gen = get_embedding_generator()
    vec = gen.embed_text("Patient exhibits elevated blood glucose levels.")
    assert len(vec) == 384
    norm = sum(x * x for x in vec)
    assert abs(norm - 1.0) < 1e-3


def test_embeddings_semantic_similarity():
    """Verify semantically related medical concepts yield higher cosine similarity than unrelated concepts."""
    gen = get_embedding_generator()
    v_query = gen.embed_text("cardiovascular hypertension blood pressure")
    v_related = gen.embed_text("high blood pressure systolic diastolic reading")
    v_unrelated = gen.embed_text("astrophysics planetary orbits astronomy")

    def dot_product(a, b):
        return sum(x * y for x, y in zip(a, b))

    sim_rel = dot_product(v_query, v_related)
    sim_unrel = dot_product(v_query, v_unrelated)

    assert sim_rel > sim_unrel


def test_llm_gateway_grounded_extractive_synthesis():
    """Verify extractive synthesis produces citations and grounded response."""
    gateway = LLMGateway()

    doc = Document(
        title="Cardiovascular Treatment Guidelines 2026",
        filename="cv_guidelines.txt",
        file_type="txt",
        file_size_bytes=1000,
        storage_path="/virtual/cv.txt",
        is_public=True
    )
    chunk = DocumentChunk(
        chunk_index=0,
        content="Primary hypertension first-line medication is Lisinopril 10mg daily. Monitor renal function every 6 months.",
        embedding=[0.0] * 384
    )

    retrieved = [(chunk, doc, 0.85)]
    query = "What is the first line medication for hypertension?"

    answer, evidence_found = gateway._grounded_extractive_synthesis(query, retrieved)
    assert evidence_found is True
    assert "Lisinopril" in answer
    assert "Cardiovascular Treatment Guidelines 2026" in answer
    assert "Chunk #0" in answer


def test_llm_gateway_insufficient_evidence():
    """Verify gateway indicates lack of evidence when no matching chunks exist."""
    gateway = LLMGateway()
    answer, evidence_found = gateway._grounded_extractive_synthesis("What is the protocol for rare disease X?", [])
    assert evidence_found is False
    assert "do not have sufficient clinical or technical documentation" in answer
