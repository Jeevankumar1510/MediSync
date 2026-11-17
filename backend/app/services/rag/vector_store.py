import logging
import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.user import User, UserRole
from app.schemas.rag import SourceReference

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Manages vector storage and pgvector similarity queries for document chunks,
    enforcing Document Access Control (ACL) rules.
    """

    @staticmethod
    async def search_similar_chunks(
        db: AsyncSession,
        query_vector: List[float],
        user: User,
        top_k: int = 4,
        filter_document_ids: Optional[List[uuid.UUID]] = None,
        min_similarity: float = 0.30
    ) -> List[Tuple[DocumentChunk, Document, float]]:
        """
        Performs semantic similarity search over indexed chunks using pgvector cosine distance.
        Enforces Document Access Control (ACL):
        - Superusers and ADMINs can access all indexed documents.
        - Other roles can only access documents where is_public == True OR user_id == current_user.id.
        """
        # Base query joining DocumentChunk to Document
        distance_expr = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
        
        stmt = (
            select(DocumentChunk, Document, distance_expr)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(Document.status == DocumentStatus.INDEXED)
        )

        # Enforce Document Access Control (ACL)
        is_admin_or_super = user.is_superuser or (user.role == UserRole.ADMIN)
        if not is_admin_or_super:
            stmt = stmt.where(
                or_(
                    Document.is_public == True,
                    Document.user_id == user.id
                )
            )

        # Filter by specific document IDs if provided
        if filter_document_ids:
            stmt = stmt.where(Document.id.in_(filter_document_ids))

        # Order by closest cosine distance first
        stmt = stmt.order_by(distance_expr).limit(top_k * 2)

        result = await db.execute(stmt)
        rows = result.all()

        matched_results: List[Tuple[DocumentChunk, Document, float]] = []
        for chunk, doc, dist in rows:
            # Cosine distance to similarity: 1.0 - distance
            similarity = round(max(0.0, 1.0 - float(dist)), 4) if dist is not None else 0.0
            if similarity >= min_similarity:
                matched_results.append((chunk, doc, similarity))
                if len(matched_results) >= top_k:
                    break

        return matched_results

    @staticmethod
    def format_sources(matched_results: List[Tuple[DocumentChunk, Document, float]]) -> List[SourceReference]:
        """Converts matched chunk-document tuples into structured SourceReference schemas."""
        sources = []
        for chunk, doc, sim in matched_results:
            snippet = chunk.content[:200] + ("..." if len(chunk.content) > 200 else "")
            sources.append(
                SourceReference(
                    document_id=doc.id,
                    document_title=doc.title,
                    chunk_index=chunk.chunk_index,
                    similarity_score=sim,
                    snippet=snippet
                )
            )
        return sources
