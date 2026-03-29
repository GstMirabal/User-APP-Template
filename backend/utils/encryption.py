from __future__ import annotations

import hashlib
import hmac
from typing import TYPE_CHECKING

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.utils.encoding import force_bytes, force_str

if TYPE_CHECKING:
    pass


def get_fernet() -> Fernet:
    """Returns a Fernet instance using the MASTER_KEY from settings.

    Ensures the key is properly formatted (32 url-safe base64-encoded bytes).

    Returns:
        Fernet: An initialized Fernet instance.

    Raises:
        ValueError: If MASTER_KEY is not configured in settings.
    """
    key: str | bytes = settings.MASTER_KEY
    if not key:
        raise ValueError("MASTER_KEY is not configured in settings.")
    return Fernet(key)


def encrypt_value(value: str | None) -> str | None:
    """Encrypts a string value using Fernet (symmetric encryption).

    Returns the encrypted value as a base64 encoded string.

    Args:
        value (Optional[str]): The plain text string to encrypt.

    Returns:
        Optional[str]: The encrypted base64 string, or None if input was None.
    """
    if value is None:
        return None

    f: Fernet = get_fernet()
    # Fernet encrypt expects bytes
    encrypted_bytes: bytes = f.encrypt(force_bytes(value))
    # Return string for storage in TextField
    return force_str(encrypted_bytes)


def decrypt_value(token: str | None) -> str | None:
    """Decrypts a base64 encoded string token back to the original string value.

    Args:
        token (Optional[str]): The encrypted base64 string to decrypt.

    Returns:
        Optional[str]: The decrypted plain text string, or None if input was None.

    Raises:
        InvalidToken: If the decryption fails due to an invalid key or corrupted data.
    """
    if token is None:
        return None

    f: Fernet = get_fernet()
    try:
        decrypted_bytes: bytes = f.decrypt(force_bytes(token))
        return force_str(decrypted_bytes)
    except InvalidToken:
        # Re-raising for specific handling at the caller level if necessary.
        raise


def generate_blind_index(value: str | None) -> str | None:
    """Generates a deterministic blind index for a given value using HMAC-SHA256.

    This allows searching for exact matches without exposing the raw value.

    Args:
        value (Optional[str]): The plain text string to hash.

    Returns:
        Optional[str]: The HMAC-SHA256 hex digest, or None if input was None.

    Raises:
        ValueError: If ENCRYPTION_PEPPER is not configured in settings.
    """
    if value is None:
        return None

    pepper: str | bytes = settings.ENCRYPTION_PEPPER
    if not pepper:
        raise ValueError("ENCRYPTION_PEPPER is not configured in settings.")

    # HMAC-SHA256
    # Key: PEPPER (bytes)
    # Message: value (bytes)
    h = hmac.new(force_bytes(pepper), force_bytes(value), hashlib.sha256)
    return h.hexdigest()
