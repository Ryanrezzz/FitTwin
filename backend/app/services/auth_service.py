"""Auth use-cases: register, authenticate, issue/rotate tokens.

Knows nothing about HTTP — it raises `AuthError` (mapped to 401 by the router)
and returns domain objects/tokens. Storage is behind `UserRepo`.
"""
from __future__ import annotations

from app.core.google_oauth import GoogleIdentity, verify_id_token
from app.core.security import (
    AuthError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repo import UserRepo


class EmailTakenError(Exception):
    """Registration with an already-registered email; router maps to 409."""


class AuthService:
    def __init__(self, users: UserRepo) -> None:
        self._users = users

    async def register(self, *, email: str, password: str) -> User:
        if await self._users.get_by_email(email) is not None:
            raise EmailTakenError(email)
        return await self._users.create(email=email, password_hash=hash_password(password))

    async def authenticate(self, *, email: str, password: str) -> User:
        user = await self._users.get_by_email(email)
        # A Google-only account has `password_hash = None`. Treating that as
        # "no password required" would let anyone in with an empty string, so
        # the absence of a hash is an explicit rejection, not a fallthrough.
        if user is None or not user.password_hash:
            raise AuthError("Invalid email or password")
        if not verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")
        if not user.is_active:
            raise AuthError("Account is disabled")
        return user

    # ── Google Sign-In ───────────────────────────────────────────────────────
    async def sign_in_with_google(self, credential: str) -> tuple[User, bool]:
        """Verify a Google ID token, then find-or-link-or-create the account.

        Returns `(user, created)`.

        Resolution order matters:

        1. **By `google_sub`** — the stable identifier. A user who changed their
           Gmail address must still land on their own account.
        2. **By verified email** — links Google to an existing password account.
           Safe only because `verify_id_token` refuses unverified addresses;
           linking on an unverified email would be account takeover by design.
        3. **Otherwise create** a passwordless account.

        Linking is deliberately additive: an existing password keeps working, so
        the user can still sign in either way afterwards.
        """
        identity: GoogleIdentity = verify_id_token(credential)

        user = await self._users.get_by_google_sub(identity.sub)
        if user is not None:
            if not user.is_active:
                raise AuthError("Account is disabled")
            return await self._sync_profile(user, identity), False

        existing = await self._users.get_by_email(identity.email)
        if existing is not None:
            if not existing.is_active:
                raise AuthError("Account is disabled")
            existing.google_sub = identity.sub
            existing.email_verified = True
            return await self._sync_profile(existing, identity), False

        created = await self._users.create(
            email=identity.email,
            password_hash=None,          # passwordless by construction
            google_sub=identity.sub,
            email_verified=True,
            display_name=identity.name,
            avatar_url=identity.picture,
        )
        return created, True

    async def _sync_profile(self, user: User, identity: GoogleIdentity) -> User:
        """Refresh the display fields Google owns; never touch credentials."""
        user.display_name = identity.name or user.display_name
        user.avatar_url = identity.picture or user.avatar_url
        return await self._users.save(user)

    def issue_tokens(self, user: User) -> tuple[str, str]:
        sub = str(user.id)
        return create_access_token(sub, role=user.role.value), create_refresh_token(sub)

    async def refresh_access(self, refresh_token: str) -> str:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = await self._users.get_by_id(payload["sub"])
        if user is None or not user.is_active:
            raise AuthError("User no longer valid")
        return create_access_token(str(user.id), role=user.role.value)
