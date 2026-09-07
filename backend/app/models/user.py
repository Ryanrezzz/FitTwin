"""User document — the auth root.

Deliberately small and PII-free of profile data (see docs/03-data-model.md): an
auth/login read shouldn't drag the whole profile/plan along. The profile is a
separate 1:1 document keyed by `user_id`.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from beanie import Document
from pydantic import EmailStr, Field
from pymongo import IndexModel


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Role(str, Enum):
    user = "user"
    coach = "coach"
    admin = "admin"


class AuthProvider(str, Enum):
    password = "password"
    google = "google"


class User(Document):
    email: EmailStr

    # None for accounts that only ever signed in with Google. Password login MUST
    # reject these rather than treating "no hash" as "no password required" —
    # see AuthService.authenticate.
    password_hash: str | None = None

    # Google's `sub`: stable, immutable, and the correct join key. Email is not —
    # a Google account can change its address, and matching on email alone is how
    # account-takeover bugs happen.
    google_sub: str | None = None

    # True only when the identity provider asserted it. Gates account linking.
    email_verified: bool = False

    display_name: str = ""
    avatar_url: str = ""

    role: Role = Role.user
    is_active: bool = True
    created_at: datetime = Field(default_factory=_utcnow)

    @property
    def providers(self) -> list[str]:
        """Which sign-in methods this account can currently use."""
        out = []
        if self.password_hash:
            out.append(AuthProvider.password.value)
        if self.google_sub:
            out.append(AuthProvider.google.value)
        return out

    class Settings:
        name = "users"
        indexes = [
            IndexModel([("email", 1)], unique=True, name="uq_user_email"),
            # PARTIAL, not sparse. Beanie serialises `google_sub: None` as an
            # explicit null rather than omitting the field, and a sparse index
            # only skips *missing* fields — so every password-only user would
            # collide on null under `unique + sparse`. Filtering on $type:
            # "string" indexes exactly the accounts that really have a Google id.
            IndexModel(
                [("google_sub", 1)],
                unique=True,
                name="uq_user_google_sub",
                partialFilterExpression={"google_sub": {"$type": "string"}},
            ),
        ]
