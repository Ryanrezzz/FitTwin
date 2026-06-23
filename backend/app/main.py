"""FastAPI application factory.

Wires the HTTP boundary onto the already-tested agent graph: lifespan compiles
the LangGraph once (singleton on `app.state`), middleware mints a request id, and
exception handlers normalize every error into one envelope. Persistence, auth and
SSE chat layer on later — see docs/04-backend.md and docs/07-roadmap.md.

Run locally:  cd backend && .venv/bin/uvicorn app.main:app --reload
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.agents.graph import build_graph
from app.api.router import api_v1
from app.api.routes import health
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Compile the LangGraph once; reused across all requests (it is stateless).
    app.state.graph = build_graph()
    yield
    app.state.graph = None


app = FastAPI(title="FitTwin API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Mint/propagate a request id and echo it on the response for tracing."""
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def _envelope(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return _envelope(request, 422, "VALIDATION_ERROR", "Request failed validation.")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return _envelope(request, exc.status_code, "HTTP_ERROR", str(exc.detail))


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    return _envelope(request, 500, "INTERNAL_ERROR", "An unexpected error occurred.")


# Liveness at root for probes/load balancers, plus the full versioned API.
app.include_router(health.router)
app.include_router(api_v1, prefix=settings.api_v1_prefix)
