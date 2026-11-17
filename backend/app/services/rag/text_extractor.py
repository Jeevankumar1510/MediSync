import io
import json
import logging
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Tuple

logger = logging.getLogger(__name__)


def extract_text_from_file(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """
    Extracts plain text from raw file bytes.
    Supports .txt, .md, .csv, .json, and .docx formats.
    
    Returns:
        Tuple[str, str]: (extracted_text, detected_file_type)
    """
    if not file_bytes:
        raise ValueError("File content is empty")

    ext = filename.lower().split(".")[-1] if "." in filename else ""
    extracted_text = ""
    file_type = ext or "unknown"

    if ext in ["txt", "md", "markdown", "csv", "tsv"]:
        extracted_text = _extract_plain_text(file_bytes)
        file_type = "txt" if ext in ["txt", "csv", "tsv"] else "md"

    elif ext == "json":
        extracted_text = _extract_json_text(file_bytes)
        file_type = "json"

    elif ext == "docx":
        extracted_text = _extract_docx_text(file_bytes)
        file_type = "docx"

    elif ext == "pdf":
        extracted_text = _extract_pdf_text(file_bytes)
        file_type = "pdf"

    else:
        # Fallback to UTF-8 decoding for any text-like format
        try:
            extracted_text = _extract_plain_text(file_bytes)
            file_type = "txt"
        except Exception as e:
            raise ValueError(f"Unsupported file format '.{ext}'. Supported formats are: .txt, .md, .json, .docx, .csv")

    cleaned_text = clean_text(extracted_text)
    if not cleaned_text:
        raise ValueError("Extracted text is empty or contains only whitespace")

    return cleaned_text, file_type


def _extract_plain_text(file_bytes: bytes) -> str:
    """Decode raw bytes using UTF-8 with fallback to latin-1."""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1", errors="replace")


def _extract_json_text(file_bytes: bytes) -> str:
    """Parse JSON and produce a structured readable text representation."""
    raw_str = _extract_plain_text(file_bytes)
    try:
        data = json.loads(raw_str)
        # Format as indented readable JSON for RAG context
        return json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        return raw_str


def _extract_docx_text(file_bytes: bytes) -> str:
    """
    Extracts text paragraphs from a Word (.docx) document using built-in standard library
    zipfile and xml.etree.ElementTree, requiring no external paid or heavy dependencies.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
            if "word/document.xml" not in docx_zip.namelist():
                raise ValueError("Invalid .docx file: word/document.xml missing")
            
            xml_content = docx_zip.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            
            # WordprocessingML namespace
            namespaces = {
                "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            }
            
            paragraphs = []
            for p in tree.findall(".//w:p", namespaces):
                texts = [node.text for node in p.findall(".//w:t", namespaces) if node.text]
                p_text = "".join(texts).strip()
                if p_text:
                    paragraphs.append(p_text)
                    
            return "\n\n".join(paragraphs)
    except Exception as e:
        logger.error(f"Error extracting docx text: {e}")
        raise ValueError(f"Failed to parse .docx document: {str(e)}")


def _extract_pdf_text(file_bytes: bytes) -> str:
    """
    Extracts text from PDF. Tries pypdf if installed; falls back to basic stream text extraction.
    """
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages_text = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pages_text.append(t)
        return "\n\n".join(pages_text)
    except ImportError:
        # Fallback heuristic: search for ASCII / UTF-8 strings within PDF streams
        text = file_bytes.decode("latin-1", errors="ignore")
        # Extract plain strings inside parentheses often found in PDF BT...ET text objects
        matches = re.findall(r"\(([\w\s.,;:?!'\"-]{4,})\)", text)
        if matches:
            return "\n".join(matches)
        raise ValueError("PDF parsing requires pypdf or a plain-text PDF format.")


def clean_text(text: str) -> str:
    """Normalizes whitespace, removes null bytes and excessive newlines."""
    if not text:
        return ""
    # Remove null characters
    text = text.replace("\x00", "")
    # Normalize carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple consecutive newlines (more than 2) to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing and leading whitespace
    return text.strip()
