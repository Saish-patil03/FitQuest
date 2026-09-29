import os
import hashlib
import hmac
import time
import json
import base64
from typing import Optional, Tuple
def get_secret_key() -> str:
    """
    Retrieves the application secret key from settings or environment.
    Fails safely with a RuntimeError if FITQUEST_SECRET_KEY is missing.
    """
    from backend.config import settings
    key = settings.FITQUEST_SECRET_KEY or os.environ.get("FITQUEST_SECRET_KEY")
    if not key or not key.strip():
        raise RuntimeError(
            "FITQUEST_SECRET_KEY environment variable is not configured. "
            "Please set a secure FITQUEST_SECRET_KEY in your .env file or environment."
        )
    return key.strip()

def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using PBKDF2-HMAC-SHA256 with a 16-byte random salt and 100,000 iterations.
    """
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{pwd_hash.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifies a plain-text password against a stored PBKDF2-HMAC-SHA256 hash.
    """
    if not stored_hash or ":" not in stored_hash:
        return False
    try:
        salt_hex, hash_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(pwd_hash.hex(), hash_hex)
    except Exception:
        return False

def create_access_token(user_id: int, expires_in_seconds: int = 86400 * 30) -> str:
    """
    Creates a signed HMAC-SHA256 URL-safe session token containing user_id and expiration.
    """
    secret_key = get_secret_key()
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "exp": int(time.time()) + expires_in_seconds
    }

    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).decode("utf-8").rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")

    signature_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret_key.encode("utf-8"), signature_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")

    return f"{header_b64}.{payload_b64}.{sig_b64}"

def verify_access_token(token: str) -> Optional[int]:
    """
    Verifies signature and expiration of an access token, returning the authenticated user_id.
    """
    if not token or token.count(".") != 2:
        return None
    try:
        secret_key = get_secret_key()
        parts = token.split(".")
        header_b64, payload_b64, sig_b64 = parts[0], parts[1], parts[2]

        signature_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(secret_key.encode("utf-8"), signature_input, hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")

        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None

        padding = "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))

        if payload.get("exp", 0) < time.time():
            return None

        return int(payload["sub"])
    except Exception:
        return None

def generate_reset_token() -> str:
    """
    Generates a cryptographically secure 32-byte URL-safe random string for password reset.
    """
    import secrets
    return secrets.token_urlsafe(32)

def hash_reset_token(token: str) -> str:
    """
    Computes SHA-256 hex digest of a password reset token for safe storage in the database.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

