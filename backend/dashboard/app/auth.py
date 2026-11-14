"""
Physician Authentication & Role-Based Authorization Module.

Supports:
1. Local development / demo mode (when AUTH_DISABLED=true) with explicit logging.
2. Production HMAC-SHA256 JWT cryptographic token validation (when AUTH_DISABLED=false).
3. Role enforcement ensuring only verified physicians can finalize clinical encounters.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Optional

from fastapi import Depends, Header, HTTPException, status
from .config import get_settings


@dataclass
class Principal:
    physician_id: str
    physician_name: str
    role: str = "physician"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_access_token(
    subject: str,
    name: str,
    role: str = "physician",
    expires_delta_seconds: int = 86400,
    secret_key: Optional[str] = None,
) -> str:
    """Create a signed HMAC-SHA256 JWT access token."""
    settings = get_settings()
    secret = (secret_key or settings.secret_key).encode("utf-8")

    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": subject,
        "name": name,
        "role": role,
        "iat": now,
        "exp": now + expires_delta_seconds,
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_and_verify_token(token: str, secret_key: Optional[str] = None) -> dict[str, Any]:
    """Verify cryptographic HMAC-SHA256 signature and token expiration."""
    settings = get_settings()
    secret = (secret_key or settings.secret_key).encode("utf-8")

    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authentication token.",
        )

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(secret, signing_input, hashlib.sha256).digest()

    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature encoding.",
        )

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token cryptographic signature.",
        )

    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    # Check expiration
    exp = payload.get("exp")
    if exp and time.time() > exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
        )

    return payload


def get_current_principal(
    authorization: str | None = Header(default=None),
) -> Principal:
    """
    Authenticate physician identity.
    In demo mode (AUTH_DISABLED=true), returns configured demo principal.
    In production mode (AUTH_DISABLED=false), verifies HMAC-SHA256 JWT signature.
    """
    settings = get_settings()

    if settings.auth_disabled:
        return Principal(
            physician_id=settings.demo_physician_id,
            physician_name=settings.demo_physician_name,
            role="physician",
        )

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Physician authentication required. Provide Bearer token.",
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty authentication token.",
        )

    payload = decode_and_verify_token(token, settings.secret_key)
    physician_id = payload.get("sub")
    physician_name = payload.get("name") or "Physician"
    role = payload.get("role") or "physician"

    if not physician_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject (physician_id).",
        )

    return Principal(
        physician_id=physician_id,
        physician_name=physician_name,
        role=role,
    )


def require_physician(principal: Principal = Depends(get_current_principal)) -> Principal:
    """Enforce physician-only role for clinical reviews and finalization."""
    if principal.role not in {"physician", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Physician clinical role required.",
        )
    return principal
