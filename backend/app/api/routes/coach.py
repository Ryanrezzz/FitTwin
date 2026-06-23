"""Coach routes — the HTTP boundary over the agent graph.

Stateless for now: the caller supplies profile/history/active_plan in the body,
the service drives the graph, and we return the composed response + agent trace.
Auth + per-user persistence (load profile, store versioned plan) wrap this same
service in a later sprint without changing the agent layer.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import get_coach_service
from app.schemas.coach import (
    ChatRequest,
    CoachResponseOut,
    GeneratePlanRequest,
    WeeklyReviewRequest,
)
from app.services.coach_service import CoachService

router = APIRouter(tags=["coach"])

# `user_id` is hard-coded until auth lands; the service already threads it through
# so swapping in `Depends(get_current_user)` is the only change needed.
_DEMO_USER = "demo"


@router.post("/plans/generate", response_model=CoachResponseOut)
def generate_plan(
    req: GeneratePlanRequest,
    service: CoachService = Depends(get_coach_service),
) -> CoachResponseOut:
    """Run nutrition + workout + safety to produce the first plan from a profile."""
    return service.generate_plan(req, user_id=_DEMO_USER)


@router.post("/plans/weekly-review", response_model=CoachResponseOut)
def weekly_review(
    req: WeeklyReviewRequest,
    service: CoachService = Depends(get_coach_service),
) -> CoachResponseOut:
    """Analyze logged data; re-plan if a plateau is detected, else motivate."""
    return service.weekly_review(req, user_id=_DEMO_USER)


@router.post("/chat", response_model=CoachResponseOut)
def chat(
    req: ChatRequest,
    service: CoachService = Depends(get_coach_service),
) -> CoachResponseOut:
    """Route a free-text message through the orchestrator to the right agents."""
    return service.chat(req, user_id=_DEMO_USER)
