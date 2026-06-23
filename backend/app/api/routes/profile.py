"""Profile routes — onboarding read/write for the authenticated user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import ensure_persistence, get_current_user, get_profile_repo
from app.models.user import User
from app.repositories.profile_repo import ProfileRepo
from app.schemas.coach import ProfileIn, ProfileOut

router = APIRouter(prefix="/profile", tags=["profile"], dependencies=[Depends(ensure_persistence)])


@router.get("", response_model=ProfileOut)
async def get_profile(
    user: User = Depends(get_current_user),
    profiles: ProfileRepo = Depends(get_profile_repo),
) -> ProfileOut:
    profile = await profiles.get_by_user(str(user.id))
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No profile yet — PUT to create one.")
    return ProfileOut(**profile.to_agent_profile())


@router.put("", response_model=ProfileOut)
async def upsert_profile(
    body: ProfileIn,
    user: User = Depends(get_current_user),
    profiles: ProfileRepo = Depends(get_profile_repo),
) -> ProfileOut:
    profile = await profiles.upsert(str(user.id), body.model_dump())
    return ProfileOut(**profile.to_agent_profile())
