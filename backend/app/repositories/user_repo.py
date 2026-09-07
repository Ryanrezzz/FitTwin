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
    async def get_by_google_sub(self, google_sub: str) -> User | None: ...
    async def create(
        self,
        *,
        email: str,
        password_hash: str | None = None,
        role: Role = Role.user,
        google_sub: str | None = None,
        email_verified: bool = False,
        display_name: str = "",
        avatar_url: str = "",
    ) -> User: ...
    async def save(self, user: User) -> User: ...


class BeanieUserRepo:
    async def get_by_id(self, user_id: str) -> User | None:
        try:
            oid = PydanticObjectId(user_id)
        except Exception:  # noqa: BLE001 — malformed id is simply "not found"
            return None
        return await User.get(oid)

    async def get_by_email(self, email: str) -> User | None:
        return await User.find_one(User.email == email)

    async def get_by_google_sub(self, google_sub: str) -> User | None:
        return await User.find_one(User.google_sub == google_sub)

    async def create(
        self,
        *,
        email: str,
        password_hash: str | None = None,
        role: Role = Role.user,
        google_sub: str | None = None,
        email_verified: bool = False,
        display_name: str = "",
        avatar_url: str = "",
    ) -> User:
        return await User(
            email=email,
            password_hash=password_hash,
            role=role,
            google_sub=google_sub,
            email_verified=email_verified,
            display_name=display_name,
            avatar_url=avatar_url,
        ).insert()

    async def save(self, user: User) -> User:
        await user.save()
        return user
