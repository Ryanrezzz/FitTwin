"""Coach routes — the HTTP boundary over the agent graph.

Authenticated. Profile and the active plan are loaded from the current user's
stored data (not the request body); a complete run is persisted as a new plan
version. History still arrives in the body until daily logs are persisted.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import (
    ensure_persistence,
    get_active_plan,
    get_coach_service,
    get_current_profile,
    get_current_user,
    get_plan_repo,
)
from app.models.user import User
from app.repositories.plan_repo import PlanRepo
from app.schemas.coach import ChatRequest, CoachResponseOut, PlanOut, WeeklyReviewRequest
from app.services.coach_service import CoachService

router = APIRouter(tags=["coach"], dependencies=[Depends(ensure_persistence)])


def _plan_out(plan: Any) -> PlanOut:
    return PlanOut(
        id=str(plan.id),
        version=plan.version,
        active=plan.active,
        intent=plan.intent,
        calorie_target=plan.calorie_target,
        macros=plan.macros,
        nutrition=plan.nutrition,
        workout=plan.workout,
        degraded=plan.degraded,
        created_at=plan.created_at,
    )


@router.post("/plans/generate", response_model=CoachResponseOut)
async def generate_plan(
    user: User = Depends(get_current_user),
    profile: dict[str, Any] = Depends(get_current_profile),
    service: CoachService = Depends(get_coach_service),
) -> CoachResponseOut:
    """Run nutrition + workout + safety, then persist the plan as a new version."""
    return await service.generate_plan(profile=profile, user_id=str(user.id))


@router.post("/plans/weekly-review", response_model=CoachResponseOut)
async def weekly_review(
    req: WeeklyReviewRequest,
    user: User = Depends(get_current_user),
    profile: dict[str, Any] = Depends(get_current_profile),
    active_plan: dict[str, Any] | None = Depends(get_active_plan),
    service: CoachService = Depends(get_coach_service),
) -> CoachResponseOut:
    """Analyze logged data against the active plan; re-plan on a plateau, else motivate."""
    return await service.weekly_review(
        req, profile=profile, active_plan=active_plan, user_id=str(user.id)
    )


@router.post("/chat", response_model=CoachResponseOut)
async def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    profile: dict[str, Any] = Depends(get_current_profile),
    active_plan: dict[str, Any] | None = Depends(get_active_plan),
    service: CoachService = Depends(get_coach_service),
) -> CoachResponseOut:
    """Route a free-text message through the orchestrator to the right agents."""
    return await service.chat(req, profile=profile, active_plan=active_plan, user_id=str(user.id))


# Declared before /plans/{plan_id} so "active" isn't matched as an id.
@router.get("/plans/active", response_model=PlanOut)
async def active_plan(
    user: User = Depends(get_current_user),
    plans: PlanRepo = Depends(get_plan_repo),
) -> PlanOut:
    plan = await plans.get_active(str(user.id))
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active plan — generate one first.")
    return _plan_out(plan)


@router.get("/plans/{plan_id}", response_model=PlanOut)
async def get_plan(
    plan_id: str,
    user: User = Depends(get_current_user),
    plans: PlanRepo = Depends(get_plan_repo),
) -> PlanOut:
    plan = await plans.get_by_id(plan_id, str(user.id))
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found.")
    return _plan_out(plan)
