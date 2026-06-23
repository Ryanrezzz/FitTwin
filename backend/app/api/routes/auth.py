"""Auth routes — register, login, refresh, me.

Thin HTTP boundary: validate input, call AuthService, map domain errors to status
codes. `password_hash` is never serialized (UserOut has no such field).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import AuthError
from app.deps import ensure_persistence, get_auth_service, get_current_user
from app.models.user import User
from app.schemas.auth import (
    AccessToken,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.services.auth_service import AuthService, EmailTakenError

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(ensure_persistence)])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id),
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    auth: AuthService = Depends(get_auth_service),
) -> UserOut:
    try:
        user = await auth.register(email=req.email, password=req.password)
    except EmailTakenError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from e
    return _user_out(user)


@router.post("/login", response_model=TokenPair)
async def login(
    req: LoginRequest,
    auth: AuthService = Depends(get_auth_service),
) -> TokenPair:
    try:
        user = await auth.authenticate(email=req.email, password=req.password)
    except AuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    access, refresh = auth.issue_tokens(user)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=AccessToken)
async def refresh(
    req: RefreshRequest,
    auth: AuthService = Depends(get_auth_service),
) -> AccessToken:
    try:
        access = await auth.refresh_access(req.refresh_token)
    except AuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    return AccessToken(access_token=access)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)
