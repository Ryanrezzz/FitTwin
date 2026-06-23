"""Password hashing (Argon2id) and JWT encode/decode.

Pure functions over `settings` — no I/O, no FastAPI — so they're trivially
unit-testable. Access tokens are short-lived; refresh tokens are longer and
carry `type=refresh` so an access token can never be replayed as a refresh.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher

from app.config import settings

_hasher = PasswordHasher()


class AuthError(Exception):
    """Raised on invalid credentials or tokens; routers map this to 401."""


# ── passwords ────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except Exception:  # noqa: BLE001 — mismatch or malformed hash both mean "no"
        return False


# ── tokens ───────────────────────────────────────────────────────────────────
def _encode(sub: str, token_type: str, ttl: timedelta, **claims: object) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
        **claims,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(sub: str, *, role: str = "user") -> str:
    return _encode(sub, "access", timedelta(minutes=settings.jwt_access_ttl_min), role=role)


def create_refresh_token(sub: str) -> str:
    return _encode(sub, "refresh", timedelta(days=settings.jwt_refresh_ttl_days))


def decode_token(token: str, *, expected_type: str) -> dict:
    """Decode + validate signature, expiry, and token type. Raises AuthError."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as e:
        raise AuthError("Invalid or expired token") from e
    if payload.get("type") != expected_type:
        raise AuthError(f"Expected a {expected_type} token")
    return payload
