import hashlib
import hmac
import logging
from typing import Optional

logger = logging.getLogger("medisync.webhook_security")


def verify_hmac_signature(
    payload_bytes: bytes,
    signature_header: Optional[str],
    secret: str,
) -> bool:
    """
    Validates HMAC-SHA256 webhook signatures using constant-time comparison to prevent timing attacks.
    Supports raw hex strings as well as 'sha256=' prefixed headers (GitHub/Stripe/Epic style).
    """
    if not signature_header or not secret:
        return False

    clean_sig = signature_header.strip()
    if clean_sig.startswith("sha256="):
        clean_sig = clean_sig.split("sha256=", 1)[1]

    expected_sig = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison
    is_valid = hmac.compare_digest(expected_sig, clean_sig)
    if not is_valid:
        logger.warning("HMAC-SHA256 signature mismatch on incoming webhook.")
    return is_valid


def generate_hmac_signature(payload_bytes: bytes, secret: str) -> str:
    """Utility to generate valid HMAC-SHA256 signatures for testing and outbound dispatch."""
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()
