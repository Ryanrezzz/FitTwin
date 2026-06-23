"""Plan repository — versioned create + active-plan reads.

`create_version` deactivates the prior active plan and inserts the next version,
so there is always at most one active plan per user. Reads are scoped to
`user_id` (object-level authz: a user can only fetch their own plans).
"""
from __future__ import annotations

from typing import Any, Protocol

from beanie import PydanticObjectId
from beanie.operators import Eq, Set

from app.models.plan import Plan


class PlanRepo(Protocol):
    async def create_version(
        self, user_id: str, *, nutrition: dict[str, Any], workout: dict[str, Any],
        intent: str | None = None, degraded: bool = False,
    ) -> Plan: ...
    async def get_active(self, user_id: str) -> Plan | None: ...
    async def get_by_id(self, plan_id: str, user_id: str) -> Plan | None: ...


class BeaniePlanRepo:
    async def create_version(
        self, user_id: str, *, nutrition: dict[str, Any], workout: dict[str, Any],
        intent: str | None = None, degraded: bool = False,
    ) -> Plan:
        oid = PydanticObjectId(user_id)
        latest = await Plan.find(Plan.user_id == oid).sort(-Plan.version).first_or_none()
        next_version = (latest.version + 1) if latest else 1
        # at most one active plan: flip the current one off before inserting the new one
        await Plan.find(Plan.user_id == oid, Eq(Plan.active, True)).update(
            Set({Plan.active: False})
        )
        return await Plan(
            user_id=oid,
            version=next_version,
            active=True,
            intent=intent,
            calorie_target=int(nutrition.get("calories", 0)),
            macros=nutrition.get("macros", {}),
            nutrition=nutrition,
            workout=workout,
            degraded=degraded,
        ).insert()

    async def get_active(self, user_id: str) -> Plan | None:
        return await Plan.find_one(
            Plan.user_id == PydanticObjectId(user_id), Eq(Plan.active, True)
        )

    async def get_by_id(self, plan_id: str, user_id: str) -> Plan | None:
        try:
            plan = await Plan.get(PydanticObjectId(plan_id))
        except Exception:  # noqa: BLE001 — malformed id => not found
            return None
        if plan is None or plan.user_id != PydanticObjectId(user_id):
            return None
        return plan
