"""Fernet encryption for sensitive data at rest (e.g. OAuth tokens).

Requires TOKEN_ENCRYPTION_KEY env var set to a Fernet key.
Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

TOKEN_ENCRYPTION_KEY = os.getenv("TOKEN_ENCRYPTION_KEY", "")

_fernet = None


def _get_fernet() -> Fernet | None:
    global _fernet
    if _fernet is not None:
        return _fernet
    if not TOKEN_ENCRYPTION_KEY:
        return None
    try:
        _fernet = Fernet(TOKEN_ENCRYPTION_KEY.encode())
        return _fernet
    except Exception:
        logger.warning("Invalid TOKEN_ENCRYPTION_KEY — token encryption disabled")
        return None


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string. Returns original value if encryption is not configured."""
    f = _get_fernet()
    if f is None:
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a string. Returns raw value if not encrypted (migration path)."""
    f = _get_fernet()
    if f is None:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        # Value was stored before encryption was enabled — return as-is
        return ciphertext


def is_encryption_configured() -> bool:
    return _get_fernet() is not None
