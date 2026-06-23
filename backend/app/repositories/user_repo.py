"""User repository — the only place (with profile_repo) that queries Beanie.

The `UserRepo` Protocol is the seam the service depends on; `BeanieUserRepo` is
the production impl. Tests inject an in-memory fake that satisfies the same
Protocol via `app.dependency_overrides`, so the service/route logic is exercised
without a live Mongo.
"""
from __future__ import annotations

from typing import Protocol

from beanie import PydanticObjectId

from app.models.user import Role, User


class UserRepo(Protocol):
    async def get_by_id(self, user_id: str) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def create(self, *, email: str, password_hash: str, role: Role = Role.user) -> User: ...


class BeanieUserRepo:
    async def get_by_id(self, user_id: str) -> User | None:
        try:
            oid = PydanticObjectId(user_id)
        except Exception:  # noqa: BLE001 — malformed id is simply "not found"
            return None
        return await User.get(oid)

    async def get_by_email(self, email: str) -> User | None:
        return await User.find_one(User.email == email)

    async def create(self, *, email: str, password_hash: str, role: Role = Role.user) -> User:
        return await User(email=email, password_hash=password_hash, role=role).insert()
