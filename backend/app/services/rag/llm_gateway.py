import logging
import re
from typing import List, Tuple, Optional
import httpx

from app.config import settings
from app.models.document import Document, DocumentChunk
from app.schemas.rag import SourceReference

logger = logging.getLogger(__name__)


class LLMGateway:
    """
    Healthcare LLM Gateway.
    Routes queries to Groq, Ollama, OpenAI, or Gemini if configured.
    Falls back gracefully to a high-precision Grounded Extractive Synthesizer
    to ensure 100% free, zero-paid-dependency, offline reliability.
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.groq_api_key = settings.GROQ_API_KEY
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.openai_api_key = settings.OPENAI_API_KEY
        self.gemini_api_key = settings.GEMINI_API_KEY

    async def generate_response(
        self,
        query: str,
        retrieved_chunks: List[Tuple[DocumentChunk, Document, float]]
    ) -> Tuple[str, bool]:
        """
        Synthesizes an answer to `query` grounded strictly in `retrieved_chunks`.

        Returns:
            Tuple[str, bool]: (answer_text, evidence_found)
        """
        if not retrieved_chunks:
            return (
                "I do not have sufficient clinical or technical documentation in the indexed knowledge base "
                "to answer your inquiry with confidence. Please upload relevant clinical guidelines, FHIR specifications, "
                "or patient records to enable accurate retrieval.",
                False
            )

        # Build grounded context
        context_blocks = []
        for i, (chunk, doc, sim) in enumerate(retrieved_chunks, 1):
            context_blocks.append(
                f"[Source {i}: {doc.title} (Chunk #{chunk.chunk_index}, Relevance: {sim:.0%})]\n{chunk.content}"
            )
        full_context = "\n\n".join(context_blocks)

        # Attempt external LLM if configured
        if self.provider == "groq" and self.groq_api_key:
            ans = await self._call_groq(query, full_context)
            if ans:
                return ans, True

        elif self.provider == "ollama":
            ans = await self._call_ollama(query, full_context)
            if ans:
                return ans, True

        elif self.provider == "openai" and self.openai_api_key:
            ans = await self._call_openai(query, full_context)
            if ans:
                return ans, True

        elif self.provider == "gemini" and self.gemini_api_key:
            ans = await self._call_gemini(query, full_context)
            if ans:
                return ans, True

        # Grounded Extractive Synthesizer (Built-in Zero-Cost Offline Fallback)
        return self._grounded_extractive_synthesis(query, retrieved_chunks)

    def _grounded_extractive_synthesis(
        self,
        query: str,
        retrieved_chunks: List[Tuple[DocumentChunk, Document, float]]
    ) -> Tuple[str, bool]:
        """
        Performs high-precision extractive clinical synthesis from retrieved chunks.
        Strictly never hallucinates or introduces facts outside the source documents.
        """
        if not retrieved_chunks:
            return (
                "I do not have sufficient clinical or technical documentation in the indexed knowledge base "
                "to answer your inquiry with confidence.",
                False
            )

        query_words = set(re.findall(r"\w+", query.lower()))
        # Remove common query stopwords
        stopwords = {
            "what", "is", "the", "a", "an", "and", "or", "in", "of", "to", "for", "with",
            "on", "at", "by", "from", "up", "about", "into", "over", "after", "how", "why",
            "does", "do", "did", "can", "could", "should", "would", "patient", "tell", "me"
        }
        focal_terms = {w for w in query_words if len(w) > 2 and w not in stopwords}

        relevant_sentences = []
        source_citations = set()

        for chunk, doc, sim in retrieved_chunks:
            # Split chunk into sentences
            sentences = re.split(r"(?<=[.!?])\s+", chunk.content)
            for s in sentences:
                s_clean = s.strip()
                if not s_clean:
                    continue
                s_words = set(re.findall(r"\w+", s_clean.lower()))
                overlap = focal_terms.intersection(s_words)
                
                # Check if sentence is relevant to the query
                if overlap or len(sentences) == 1:
                    score = len(overlap) + sim
                    relevant_sentences.append((score, s_clean, doc.title, chunk.chunk_index))
                    source_citations.add(f"{doc.title} (Chunk #{chunk.chunk_index})")

        if not relevant_sentences:
            # Fall back to top chunk summary if similarity is good
            top_chunk, top_doc, top_sim = retrieved_chunks[0]
            if top_sim >= 0.40:
                answer = (
                    f"Based on **{top_doc.title}** (Relevance: {top_sim:.0%}):\n\n"
                    f"{top_chunk.content}\n\n"
                    f"*Sources: {top_doc.title} (Chunk #{top_chunk.chunk_index})*"
                )
                return answer, True
            return (
                "I do not have sufficient clinical or technical documentation in the indexed knowledge base "
                "to answer your inquiry with confidence.",
                False
            )

        # Sort sentences by relevance score descending and deduplicate
        relevant_sentences.sort(key=lambda x: x[0], reverse=True)
        seen_texts = set()
        chosen_lines = []
        for _, text, title, idx in relevant_sentences[:5]:
            if text not in seen_texts:
                seen_texts.add(text)
                chosen_lines.append(f"- {text} *[{title} #{idx}]*")

        citations_str = ", ".join(sorted(source_citations))
        synthesized_text = (
            f"Based on the retrieved clinical documentation:\n\n"
            + "\n".join(chosen_lines)
            + f"\n\n**Referenced Sources:** {citations_str}\n\n"
            f"> *Note: Informational summary generated from indexed documents. Strictly verify against primary clinical documentation.*"
        )

        return synthesized_text, True

    async def _call_groq(self, query: str, context: str) -> Optional[str]:
        """Call Groq API with Llama-3."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are MediSync AI, an expert clinical data assistant. "
                                    "Answer the question strictly and accurately using only the provided context. "
                                    "Cite source documents and chunk indexes. If the context does not contain sufficient "
                                    "evidence, explicitly state that information is unavailable."
                                )
                            },
                            {
                                "role": "user",
                                "content": f"Context:\n{context}\n\nQuestion: {query}"
                            }
                        ],
                        "temperature": 0.1
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"Groq API call failed: {e}")
        return None

    async def _call_ollama(self, query: str, context: str) -> Optional[str]:
        """Call local Ollama instance."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    f"{self.ollama_base_url}/api/chat",
                    json={
                        "model": "meditron",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are MediSync AI clinical assistant. Answer grounded strictly in the provided context."
                            },
                            {
                                "role": "user",
                                "content": f"Context:\n{context}\n\nQuestion: {query}"
                            }
                        ],
                        "stream": False
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    return data.get("message", {}).get("content")
        except Exception as e:
            logger.warning(f"Ollama call failed: {e}")
        return None

    async def _call_openai(self, query: str, context: str) -> Optional[str]:
        """Call OpenAI API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are MediSync AI clinical assistant. Answer grounded strictly in the provided context."
                            },
                            {
                                "role": "user",
                                "content": f"Context:\n{context}\n\nQuestion: {query}"
                            }
                        ],
                        "temperature": 0.1
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI call failed: {e}")
        return None

    async def _call_gemini(self, query: str, context: str) -> Optional[str]:
        """Call Google Gemini API."""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    url,
                    json={
                        "contents": [
                            {
                                "parts": [
                                    {
                                        "text": (
                                            f"Context:\n{context}\n\nQuestion: {query}\n\n"
                                            "Answer strictly using the provided context."
                                        )
                                    }
                                ]
                            }
                        ]
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text")
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}")
        return None
