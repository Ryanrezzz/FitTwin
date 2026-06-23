"""Dependency-injection providers.

`Depends` is the DI container: routers receive collaborators, nothing news-up its
own dependencies. The compiled LangGraph is a process-wide singleton on
`app.state`; repos default to the Beanie implementations. Tests override the repo
providers with in-memory fakes via `app.dependency_overrides`.
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.core.security import AuthError, decode_token
from app.db import db_ready
from app.models.user import Role, User
from app.repositories.plan_repo import BeaniePlanRepo, PlanRepo
from app.repositories.profile_repo import BeanieProfileRepo, ProfileRepo
from app.repositories.user_repo import BeanieUserRepo, UserRepo
from app.services.auth_service import AuthService
from app.services.coach_service import CoachService

_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


# ── infrastructure ────────────────────────────────────────────────────────────
def ensure_persistence() -> None:
    """Guard for routes that need the DB: 503 if Mongo is enabled but unreachable.

    In tests `db_enabled` is False and repos are overridden, so this is a no-op.
    """
    if settings.db_enabled and not db_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence is currently unavailable.",
        )


def get_graph(request: Request):
    """The compiled LangGraph, built once in the app lifespan (see main.py)."""
    return request.app.state.graph


def get_user_repo() -> UserRepo:
    return BeanieUserRepo()


def get_profile_repo() -> ProfileRepo:
    return BeanieProfileRepo()


def get_plan_repo() -> PlanRepo:
    return BeaniePlanRepo()


# ── services ──────────────────────────────────────────────────────────────────
def get_coach_service(
    graph=Depends(get_graph),
    plans: PlanRepo = Depends(get_plan_repo),
) -> CoachService:
    return CoachService(graph, plans)


def get_auth_service(users: UserRepo = Depends(get_user_repo)) -> AuthService:
    return AuthService(users)


# ── auth ──────────────────────────────────────────────────────────────────────
async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    users: UserRepo = Depends(get_user_repo),
) -> User:
    if creds is None:
        raise _unauthorized()
    try:
        payload = decode_token(creds.credentials, expected_type="access")
    except AuthError as e:
        raise _unauthorized(str(e)) from e
    user = await users.get_by_id(payload["sub"])
    if user is None or not user.is_active:
        raise _unauthorized("User no longer valid")
    return user


def require_role(*roles: Role):
    async def guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return guard


async def get_current_profile(
    user: User = Depends(get_current_user),
    profiles: ProfileRepo = Depends(get_profile_repo),
) -> dict[str, Any]:
    """The current user's stored profile as the agent-input dict; 400 if unset."""
    profile = await profiles.get_by_user(str(user.id))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete onboarding first (PUT /api/v1/profile).",
        )
    return profile.to_agent_profile()


async def get_active_plan(
    user: User = Depends(get_current_user),
    plans: PlanRepo = Depends(get_plan_repo),
) -> dict[str, Any] | None:
    """The current user's active plan targets for adherence/adaptation, or None."""
    plan = await plans.get_active(str(user.id))
    if plan is None:
        return None
    return {"calorie_target": plan.calorie_target, "macros": plan.macros}
