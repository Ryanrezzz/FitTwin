"""Auth routes — register, login, refresh, me.

Thin HTTP boundary: validate input, call AuthService, map domain errors to status
codes. `password_hash` is never serialized (UserOut has no such field).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.core.google_oauth import GoogleAuthUnavailable, is_configured
from app.core.ratelimit import RateLimiter
from app.core.security import AuthError
from app.deps import ensure_persistence, get_auth_service, get_current_user
from app.models.user import User
from app.schemas.auth import (
    AccessToken,
    GoogleConfigOut,
    GoogleSignInRequest,
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
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        providers=user.providers,
    )


# Credential endpoints are rate-limited per IP: login is the brute-force target,
# register is the spam/enumeration one.
@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter("register", limit=5, window_s=3600))],
)
async def register(
    req: RegisterRequest,
    auth: AuthService = Depends(get_auth_service),
) -> UserOut:
    try:
        user = await auth.register(email=req.email, password=req.password)
    except EmailTakenError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from e
    return _user_out(user)


@router.post(
    "/login",
    response_model=TokenPair,
    dependencies=[Depends(RateLimiter("login", limit=8, window_s=300))],
)
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


@router.post(
    "/refresh",
    response_model=AccessToken,
    dependencies=[Depends(RateLimiter("refresh", limit=30, window_s=300))],
)
async def refresh(
    req: RefreshRequest,
    auth: AuthService = Depends(get_auth_service),
) -> AccessToken:
    try:
        access = await auth.refresh_access(req.refresh_token)
    except AuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    return AccessToken(access_token=access)


@router.get("/google/config", response_model=GoogleConfigOut)
async def google_config() -> GoogleConfigOut:
    """Whether Google sign-in is available, and the public client id.

    The client id is public by design (it is embedded in the browser flow), so
    serving it keeps the SPA from having to duplicate build-time configuration.
    """
    return GoogleConfigOut(enabled=is_configured(), client_id=settings.google_client_id)


@router.post(
    "/google",
    response_model=TokenPair,
    dependencies=[Depends(RateLimiter("google", limit=20, window_s=300))],
)
async def google_sign_in(
    req: GoogleSignInRequest,
    auth: AuthService = Depends(get_auth_service),
) -> TokenPair:
    """Exchange a verified Google ID token for our own session tokens.

    Google authenticates the human; we still issue our own JWTs so the rest of
    the API has exactly one notion of a session.
    """
    try:
        user, _created = await auth.sign_in_with_google(req.credential)
    except GoogleAuthUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
    except AuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    access, refresh = auth.issue_tokens(user)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)
