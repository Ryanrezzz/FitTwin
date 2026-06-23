"""Coach routes — the HTTP boundary over the agent graph.

Authenticated: the profile is loaded from the current user's stored onboarding
data (not the request body). History/active_plan still arrive in the body until
daily logs + versioned plans are persisted (next sprint).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.deps import (
    ensure_persistence,
    get_coach_service,
    get_current_profile,
    get_current_user,
)
from app.models.user import User
from app.schemas.coach import ChatRequest, CoachResponseOut, WeeklyReviewRequest
from app.services.coach_service import CoachService

router = APIRouter(tags=["coach"], dependencies=[Depends(ensure_persistence)])


@router.post("/plans/generate", response_model=CoachResponseOut)
def generate_plan(
    user: User = Depends(get_current_user),
    profile: dict[str, Any] = Depends(get_current_profile),
    service: CoachService = Depends(get_coach_service),
) -> CoachResponseOut:
    """Run nutrition + workout + safety to produce the first plan from the profile."""
    return service.generate_plan(profile=profile, user_id=str(user.id))


@router.post("/plans/weekly-review", response_model=CoachResponseOut)
def weekly_review(
    req: WeeklyReviewRequest,
    user: User = Depends(get_current_user),
    profile: dict[str, Any] = Depends(get_current_profile),
    service: CoachService = Depends(get_coach_service),
) -> CoachResponseOut:
    """Analyze logged data; re-plan if a plateau is detected, else motivate."""
    return service.weekly_review(req, profile=profile, user_id=str(user.id))


@router.post("/chat", response_model=CoachResponseOut)
def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    profile: dict[str, Any] = Depends(get_current_profile),
    service: CoachService = Depends(get_coach_service),
) -> CoachResponseOut:
    """Route a free-text message through the orchestrator to the right agents."""
    return service.chat(req, profile=profile, user_id=str(user.id))
