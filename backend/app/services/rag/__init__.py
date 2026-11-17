"""
MediSync AI - Retrieval-Augmented Generation (RAG) Subsystem
Provides clinical document extraction, semantic chunking, dense vector embeddings,
pgvector similarity search, and grounded clinical synthesis.
"""

from app.services.rag.text_extractor import extract_text_from_file
from app.services.rag.chunker import chunk_text
from app.services.rag.embeddings import get_embedding_generator
from app.services.rag.vector_store import VectorStore
from app.services.rag.llm_gateway import LLMGateway

__all__ = [
    "extract_text_from_file",
    "chunk_text",
    "get_embedding_generator",
    "VectorStore",
    "LLMGateway",
]
