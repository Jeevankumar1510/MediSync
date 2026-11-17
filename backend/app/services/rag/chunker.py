import re
from typing import List, Dict, Any


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[Dict[str, Any]]:
    """
    Splits text into overlapping semantic chunks using a recursive character splitting approach.
    Prioritizes paragraph breaks (\\n\\n), line breaks (\\n), sentence boundaries (. ), and word boundaries ( ).

    Args:
        text: The source document text.
        chunk_size: Maximum character length for each chunk (default 500).
        chunk_overlap: Character overlap between consecutive chunks (default 50).

    Returns:
        List of dictionaries with keys: chunk_index, content, char_length, start_char, end_char.
    """
    if not text or not text.strip():
        return []

    if chunk_size <= chunk_overlap:
        raise ValueError("chunk_size must be strictly greater than chunk_overlap")

    text = text.strip()
    if len(text) <= chunk_size:
        return [{
            "chunk_index": 0,
            "content": text,
            "char_length": len(text),
            "start_char": 0,
            "end_char": len(text)
        }]

    # Recursive splitting primitives
    separators = ["\n\n", "\n", ". ", " "]
    raw_pieces = _split_recursive(text, separators, chunk_size)

    # Merge small pieces into cohesive chunks respecting chunk_size and chunk_overlap
    chunks: List[Dict[str, Any]] = []
    current_chunk = ""
    current_start = 0

    for piece in raw_pieces:
        if not piece:
            continue
        
        if not current_chunk:
            current_chunk = piece
            continue

        candidate = current_chunk + " " + piece if not current_chunk.endswith("\n") else current_chunk + piece
        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            # Finalize current chunk
            chunk_content = current_chunk.strip()
            if chunk_content:
                chunks.append({
                    "chunk_index": len(chunks),
                    "content": chunk_content,
                    "char_length": len(chunk_content),
                    "start_char": current_start,
                    "end_char": current_start + len(chunk_content)
                })

            # Calculate overlap starting point
            overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
            # Try to break at a word boundary within the overlap
            space_idx = overlap_text.find(" ")
            if space_idx != -1 and space_idx < len(overlap_text) - 1:
                overlap_text = overlap_text[space_idx + 1:]

            current_start += len(current_chunk) - len(overlap_text)
            current_chunk = (overlap_text + " " + piece).strip()

    # Append remaining trailing chunk
    if current_chunk.strip():
        chunk_content = current_chunk.strip()
        chunks.append({
            "chunk_index": len(chunks),
            "content": chunk_content,
            "char_length": len(chunk_content),
            "start_char": current_start,
            "end_char": current_start + len(chunk_content)
        })

    return chunks


def _split_recursive(text: str, separators: List[str], chunk_size: int) -> List[str]:
    """Recursively decomposes text using hierarchical separators."""
    if len(text) <= chunk_size or not separators:
        return [text]

    separator = separators[0]
    next_separators = separators[1:]

    parts = text.split(separator)
    result = []

    for i, part in enumerate(parts):
        if not part:
            continue
        # Re-attach separator to non-terminal parts where applicable
        formatted_part = part if i == len(parts) - 1 else part + separator
        
        if len(formatted_part) > chunk_size and next_separators:
            sub_parts = _split_recursive(formatted_part, next_separators, chunk_size)
            result.extend(sub_parts)
        else:
            result.append(formatted_part)

    return result
