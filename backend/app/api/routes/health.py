"""System endpoints — liveness vs readiness so a proxy can route correctly.

`/health` has no dependencies (always answers if the process is up). `/health/ready`
confirms the agent graph compiled; once Mongo is added it will also ping the DB.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(request: Request) -> dict:
    graph_ready = getattr(request.app.state, "graph", None) is not None
    return {"status": "ready" if graph_ready else "starting", "graph": graph_ready}
