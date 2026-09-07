"""Google Sign-In: ID-token verification.

The browser hands us a Google-issued **ID token** (a JWT). We must verify it
server-side before trusting a single claim in it. Decoding without verifying
would let anyone mint an arbitrary `email` claim and log in as any user.

`google.oauth2.id_token.verify_oauth2_token` checks, against Google's rotating
public keys:

  * the RS256 signature
  * `exp` / `iat` (not expired, not future-dated)
  * `aud` == our client id  ← THE critical one

That audience check is what stops a token minted for *some other* Google app
being replayed against us. A valid Google token is not automatically a token
*for us*, and skipping `aud` is the classic OAuth mistake.

We additionally require `iss` to be Google and `email_verified` to be true; an
unverified address must never be allowed to claim an existing account.
"""
from __future__ import annotations

from dataclasses import dataclass

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.config import settings
from app.core.security import AuthError

# Google mints tokens under either issuer; both are legitimate.
_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


class GoogleAuthUnavailable(Exception):
    """No GOOGLE_CLIENT_ID configured — the feature is off, not broken."""


@dataclass(frozen=True)
class GoogleIdentity:
    """The claims we trust after verification. `sub` is the stable join key."""

    sub: str
    email: str
    email_verified: bool
    name: str = ""
    picture: str = ""


def is_configured() -> bool:
    return bool(settings.google_client_id)


def verify_id_token(credential: str, *, transport=None) -> GoogleIdentity:
    """Verify a Google ID token and return its identity claims.

    Raises `GoogleAuthUnavailable` if the feature isn't configured, or
    `AuthError` if the token is invalid, unverified, or not addressed to us.
    """
    if not is_configured():
        raise GoogleAuthUnavailable("Google sign-in is not configured on this server.")
    if not credential or not credential.strip():
        raise AuthError("Missing Google credential")

    try:
        claims = google_id_token.verify_oauth2_token(
            credential,
            transport or google_requests.Request(),
            settings.google_client_id,   # enforces the `aud` check
        )
    except Exception as e:  # noqa: BLE001 — every failure mode is "not authenticated"
        raise AuthError("Invalid Google credential") from e

    if claims.get("iss") not in _ISSUERS:
        raise AuthError("Invalid Google credential")

    email = (claims.get("email") or "").strip().lower()
    sub = claims.get("sub") or ""
    if not sub or not email:
        raise AuthError("Google credential is missing required claims")

    # Google returns this as a bool or the string "true" depending on the path.
    verified = claims.get("email_verified")
    verified = verified is True or str(verified).lower() == "true"
    if not verified:
        raise AuthError("Your Google email address is not verified")

    return GoogleIdentity(
        sub=sub,
        email=email,
        email_verified=True,
        name=(claims.get("name") or "").strip(),
        picture=(claims.get("picture") or "").strip(),
    )
