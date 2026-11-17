from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid
from pydantic import BaseModel, Field, ConfigDict


class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    filename: str
    file_type: str
    file_size_bytes: int
    chunk_count: int = 0
    status: str
    is_public: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int


class SourceReference(BaseModel):
    document_id: uuid.UUID
    document_title: str
    chunk_index: int
    similarity_score: float
    snippet: str


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000, description="Healthcare technical or clinical inquiry")
    conversation_id: Optional[uuid.UUID] = Field(None, description="Optional conversation session ID for chat continuity")
    top_k: int = Field(4, ge=1, le=10, description="Number of relevant semantic chunks to retrieve")
    filter_document_ids: Optional[List[uuid.UUID]] = Field(None, description="Optional subset of document UUIDs to search")


class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[SourceReference] = Field(default_factory=list)
    evidence_found: bool
    conversation_id: Optional[uuid.UUID] = None
