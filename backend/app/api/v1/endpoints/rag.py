import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.database import get_db
from app.models.user import User
from app.schemas.rag import (
    DocumentListResponse,
    DocumentResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from app.services.rag_service import rag_service

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="Clinical protocol, FHIR guide, or medical document"),
    title: Optional[str] = Form(None, description="Human-readable title"),
    is_public: bool = Form(False, description="Whether accessible to all users or private to uploader"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Upload and index a healthcare document.
    Extracts text, creates overlapping semantic chunks, computes 384-d vector embeddings,
    and indexes chunks in pgvector for semantic retrieval.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )

    filename = file.filename or "uploaded_document.txt"
    doc_title = title.strip() if title and title.strip() else filename

    doc = await rag_service.ingest_document(
        db=db,
        user=current_user,
        file_bytes=file_bytes,
        filename=filename,
        title=doc_title,
        is_public=is_public,
    )
    return doc


@router.post("/query", response_model=RAGQueryResponse)
async def query_rag_assistant(
    request: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Query the MediSync AI Healthcare Assistant.
    Retrieves accessible context from pgvector using cosine distance and synthesizes
    a clinically grounded response with full source citations.
    """
    return await rag_service.query_rag(
        db=db,
        user=current_user,
        request=request
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    List accessible indexed knowledge base documents.
    Enforces Document Access Control (ACL): users see public documents and their own uploads;
    administrators have visibility across all documents.
    """
    docs, total = await rag_service.list_documents(
        db=db,
        user=current_user,
        skip=skip,
        limit=limit
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document_details(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Fetch metadata for a single indexed document."""
    doc = await rag_service.get_document(db=db, user=current_user, document_id=document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return doc


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Delete a document and all its indexed vector chunks.
    Requires ownership of the document or ADMIN role.
    """
    await rag_service.delete_document(db=db, user=current_user, document_id=document_id)
    return {
        "message": "Document and associated vector chunks deleted successfully",
        "id": str(document_id)
    }
