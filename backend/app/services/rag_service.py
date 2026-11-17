import logging
import os
import uuid
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.audit import AuditLog
from app.models.chat import Conversation, ChatMessage
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.user import User, UserRole
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse, SourceReference
from app.services.rag.chunker import chunk_text
from app.services.rag.embeddings import get_embedding_generator
from app.services.rag.llm_gateway import LLMGateway
from app.services.rag.text_extractor import extract_text_from_file
from app.services.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "documents")


class RAGService:
    """Orchestrates document ingestion, vector indexing, pgvector retrieval, and RAG synthesis."""

    def __init__(self):
        self.embedding_generator = get_embedding_generator()
        self.vector_store = VectorStore()
        self.llm_gateway = LLMGateway()
        os.makedirs(STORAGE_DIR, exist_ok=True)

    async def ingest_document(
        self,
        db: AsyncSession,
        user: User,
        file_bytes: bytes,
        filename: str,
        title: str,
        is_public: bool = False
    ) -> Document:
        """
        Validates file size, extracts text, chunks, computes embeddings,
        persists to PostgreSQL pgvector, and records HIPAA audit log.
        """
        # 1. Enforce size limit (25MB)
        max_size = 25 * 1024 * 1024
        file_size = len(file_bytes)
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds maximum permissible size of 25MB (got {file_size / (1024*1024):.2f}MB)"
            )

        # 2. Extract plain text
        try:
            extracted_text, detected_type = extract_text_from_file(file_bytes, filename)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document parsing error: {str(e)}"
            )

        # 3. Save binary locally
        doc_id = uuid.uuid4()
        storage_filename = f"{doc_id}_{filename}"
        storage_path = os.path.join(STORAGE_DIR, storage_filename)
        try:
            with open(storage_path, "wb") as f:
                f.write(file_bytes)
        except Exception as e:
            logger.error(f"Failed to save document file: {e}")
            storage_path = f"virtual://{storage_filename}"

        # 4. Create Document record
        document = Document(
            id=doc_id,
            user_id=user.id,
            title=title or filename,
            filename=filename,
            file_type=detected_type,
            file_size_bytes=file_size,
            storage_path=storage_path,
            status=DocumentStatus.PROCESSING,
            is_public=is_public,
            chunk_count=0
        )
        db.add(document)
        await db.flush()

        try:
            # 5. Semantic Chunking
            chunks = chunk_text(
                extracted_text,
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP
            )
            if not chunks:
                raise ValueError("No text content could be indexed from document.")

            # 6. Generate Dense Embeddings (Batch)
            chunk_contents = [c["content"] for c in chunks]
            embeddings = self.embedding_generator.embed_batch(chunk_contents)

            # 7. Persist Chunks with Vectors
            for c_data, emb in zip(chunks, embeddings):
                chunk_obj = DocumentChunk(
                    document_id=document.id,
                    chunk_index=c_data["chunk_index"],
                    content=c_data["content"],
                    embedding=emb,
                    chunk_metadata={
                        "char_length": c_data["char_length"],
                        "start_char": c_data["start_char"],
                        "end_char": c_data["end_char"],
                        "file_type": detected_type
                    }
                )
                db.add(chunk_obj)

            document.chunk_count = len(chunks)
            document.status = DocumentStatus.INDEXED

            # 8. HIPAA Audit Logging
            audit_entry = AuditLog(
                user_id=user.id,
                action="DOCUMENT_INGESTION",
                resource_type="Document",
                resource_id=document.id,
                details={
                    "title": document.title,
                    "filename": document.filename,
                    "file_type": document.file_type,
                    "chunk_count": document.chunk_count,
                    "is_public": document.is_public
                }
            )
            db.add(audit_entry)
            await db.commit()
            await db.refresh(document)
            return document

        except Exception as e:
            document.status = DocumentStatus.FAILED
            await db.commit()
            logger.error(f"Document ingestion failed for doc_id={document.id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process and index document chunks: {str(e)}"
            )

    async def query_rag(
        self,
        db: AsyncSession,
        user: User,
        request: RAGQueryRequest
    ) -> RAGQueryResponse:
        """
        Embeds inquiry, performs pgvector cosine similarity search respecting Document ACL,
        synthesizes grounded response, records conversation messages, and logs HIPAA audit.
        """
        # 1. Embed query vector
        query_vector = self.embedding_generator.embed_text(request.query)

        # 2. pgvector similarity search
        matched_results = await self.vector_store.search_similar_chunks(
            db=db,
            query_vector=query_vector,
            user=user,
            top_k=request.top_k,
            filter_document_ids=request.filter_document_ids
        )

        # 3. Format citations
        sources = self.vector_store.format_sources(matched_results)

        # 4. Grounded synthesis
        answer, evidence_found = await self.llm_gateway.generate_response(
            query=request.query,
            retrieved_chunks=matched_results
        )

        # 5. Conversation session persistence
        conv_id = request.conversation_id
        if conv_id:
            conv_stmt = select(Conversation).where(
                Conversation.id == conv_id,
                Conversation.user_id == user.id
            )
            res = await db.execute(conv_stmt)
            conversation = res.scalar_one_or_none()
            if not conversation:
                conversation = Conversation(
                    id=conv_id,
                    user_id=user.id,
                    title=request.query[:50]
                )
                db.add(conversation)
                await db.flush()
        else:
            conversation = Conversation(
                user_id=user.id,
                title=request.query[:50]
            )
            db.add(conversation)
            await db.flush()
            conv_id = conversation.id

        # User message
        user_msg = ChatMessage(
            conversation_id=conv_id,
            sender_role="user",
            content=request.query,
            sources=[]
        )
        db.add(user_msg)

        # Assistant message with sources
        sources_payload = [s.model_dump() for s in sources]
        assistant_msg = ChatMessage(
            conversation_id=conv_id,
            sender_role="assistant",
            content=answer,
            sources=sources_payload
        )
        db.add(assistant_msg)

        # 6. Audit Log
        audit_entry = AuditLog(
            user_id=user.id,
            action="RAG_QUERY",
            resource_type="Document",
            resource_id=None,
            details={
                "query": request.query[:100],
                "top_k": request.top_k,
                "sources_matched": len(sources),
                "evidence_found": evidence_found,
                "conversation_id": str(conv_id)
            }
        )
        db.add(audit_entry)
        await db.commit()

        return RAGQueryResponse(
            answer=answer,
            sources=sources,
            evidence_found=evidence_found,
            conversation_id=conv_id
        )

    async def list_documents(
        self,
        db: AsyncSession,
        user: User,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Document], int]:
        """Lists documents respecting Document Access Control (ACL)."""
        is_admin_or_super = user.is_superuser or (user.role == UserRole.ADMIN)

        count_stmt = select(func.count(Document.id))
        stmt = select(Document).offset(skip).limit(limit).order_by(Document.created_at.desc())

        if not is_admin_or_super:
            acl_condition = or_(
                Document.is_public == True,
                Document.user_id == user.id
            )
            count_stmt = count_stmt.where(acl_condition)
            stmt = stmt.where(acl_condition)

        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        res = await db.execute(stmt)
        docs = list(res.scalars().all())

        return docs, total

    async def get_document(
        self,
        db: AsyncSession,
        user: User,
        document_id: uuid.UUID
    ) -> Optional[Document]:
        """Fetches a document ensuring user access control."""
        stmt = select(Document).where(Document.id == document_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()

        if not doc:
            return None

        is_admin_or_super = user.is_superuser or (user.role == UserRole.ADMIN)
        if not is_admin_or_super and not doc.is_public and doc.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this document."
            )

        return doc

    async def delete_document(
        self,
        db: AsyncSession,
        user: User,
        document_id: uuid.UUID
    ) -> bool:
        """Deletes a document and its associated chunks from pgvector."""
        doc = await self.get_document(db, user, document_id)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found."
            )

        is_admin_or_super = user.is_superuser or (user.role == UserRole.ADMIN)
        if not is_admin_or_super and doc.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the document owner or an administrator can delete this document."
            )

        # Remove local file if present
        if doc.storage_path and os.path.exists(doc.storage_path):
            try:
                os.remove(doc.storage_path)
            except Exception as e:
                logger.warning(f"Failed to remove file from disk: {e}")

        # Audit log before deletion
        audit_entry = AuditLog(
            user_id=user.id,
            action="DOCUMENT_DELETED",
            resource_type="Document",
            resource_id=doc.id,
            details={
                "title": doc.title,
                "filename": doc.filename,
                "chunks_deleted": doc.chunk_count
            }
        )
        db.add(audit_entry)
        await db.delete(doc)
        await db.commit()
        return True


rag_service = RAGService()
