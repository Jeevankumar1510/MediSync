import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger("medisync.encryption")


def _get_fernet_cipher() -> Fernet:
    """Initializes a Fernet cipher instance using the configured encryption key."""
    key = settings.CREDENTIAL_ENCRYPTION_KEY
    if not key:
        raise ValueError("CREDENTIAL_ENCRYPTION_KEY is not configured in settings.")
    # Ensure key is valid bytes
    if isinstance(key, str):
        key = key.encode("utf-8")
    return Fernet(key)


def encrypt_secret(plain_text: Optional[str]) -> Optional[str]:
    """Encrypts a sensitive plaintext string (API Key, OAuth secret) into an encrypted URL-safe token."""
    if not plain_text:
        return None
    try:
        cipher = _get_fernet_cipher()
        encrypted_bytes = cipher.encrypt(plain_text.strip().encode("utf-8"))
        return encrypted_bytes.decode("utf-8")
    except Exception as exc:
        logger.error(f"Failed to encrypt secret: {exc}")
        raise ValueError(f"Secret encryption failed: {str(exc)}") from exc


def decrypt_secret(encrypted_text: Optional[str]) -> Optional[str]:
    """Decrypts a Fernet encrypted token back into its original plaintext string."""
    if not encrypted_text:
        return None
    try:
        cipher = _get_fernet_cipher()
        decrypted_bytes = cipher.decrypt(encrypted_text.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except InvalidToken:
        logger.error("Failed to decrypt secret: Invalid token or mismatched encryption key.")
        raise ValueError("Decryption failed: Invalid token or mismatched key.")
    except Exception as exc:
        logger.error(f"Secret decryption failed: {exc}")
        raise ValueError(f"Secret decryption failed: {str(exc)}") from exc
