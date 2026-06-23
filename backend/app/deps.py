"""Dependency-injection providers.

`Depends` is the DI container: routers receive collaborators, nothing news-up its
own dependencies. The compiled LangGraph is a process-wide singleton stored on
`app.state` during lifespan; tests override `get_coach_service` to inject a fake.
"""
from __future__ import annotations

from fastapi import Depends, Request

from app.services.coach_service import CoachService


def get_graph(request: Request):
    """The compiled LangGraph, built once in the app lifespan (see main.py)."""
    return request.app.state.graph


def get_coach_service(graph=Depends(get_graph)) -> CoachService:
    return CoachService(graph)
