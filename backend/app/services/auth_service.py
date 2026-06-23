"""Auth use-cases: register, authenticate, issue/rotate tokens.

Knows nothing about HTTP — it raises `AuthError` (mapped to 401 by the router)
and returns domain objects/tokens. Storage is behind `UserRepo`.
"""
from __future__ import annotations

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
        if user is None or not verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")
        if not user.is_active:
            raise AuthError("Account is disabled")
        return user

    def issue_tokens(self, user: User) -> tuple[str, str]:
        sub = str(user.id)
        return create_access_token(sub, role=user.role.value), create_refresh_token(sub)

    async def refresh_access(self, refresh_token: str) -> str:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = await self._users.get_by_id(payload["sub"])
        if user is None or not user.is_active:
            raise AuthError("User no longer valid")
        return create_access_token(str(user.id), role=user.role.value)
