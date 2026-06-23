"""Profile repository — load/upsert the 1:1 profile for a user."""
from __future__ import annotations

from typing import Any, Protocol

from beanie import PydanticObjectId

from app.models.profile import Profile


class ProfileRepo(Protocol):
    async def get_by_user(self, user_id: str) -> Profile | None: ...
    async def upsert(self, user_id: str, data: dict[str, Any]) -> Profile: ...


class BeanieProfileRepo:
    async def get_by_user(self, user_id: str) -> Profile | None:
        return await Profile.find_one(Profile.user_id == PydanticObjectId(user_id))

    async def upsert(self, user_id: str, data: dict[str, Any]) -> Profile:
        oid = PydanticObjectId(user_id)
        existing = await Profile.find_one(Profile.user_id == oid)
        if existing is None:
            return await Profile(user_id=oid, **data).insert()
        for key, value in data.items():
            setattr(existing, key, value)
        await existing.save()
        return existing
