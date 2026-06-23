"""User document — the auth root.

Deliberately small and PII-free of profile data (see docs/03-data-model.md): an
auth/login read shouldn't drag the whole profile/plan along. The profile is a
separate 1:1 document keyed by `user_id`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from beanie import Document
from pydantic import EmailStr, Field
from pymongo import IndexModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, Enum):
    user = "user"
    coach = "coach"
    admin = "admin"


class User(Document):
    email: EmailStr
    password_hash: str
    role: Role = Role.user
    is_active: bool = True
    created_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "users"
        indexes = [IndexModel([("email", 1)], unique=True, name="uq_user_email")]
