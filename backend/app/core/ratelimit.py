"""Fixed-window rate limiting for auth endpoints.

WHY: /auth/login had no limit at all — an attacker could try passwords as fast
as the network allowed. Argon2 makes each guess expensive for us too, so an
unbounded login route is a CPU-exhaustion vector as much as a credential one.

SCOPE: in-process counters, so limits are per worker. That is a real ceiling for
brute force on a single-process deployment and a meaningful speed bump on more;
a multi-worker deployment should move this to Redis (same interface).
"""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from app.config import settings

_hits: dict[str, list[float]] = defaultdict(list)
_MAX_TRACKED = 10_000


def _client_key(request: Request, scope: str) -> str:
    # X-Forwarded-For only when fronted by a proxy you trust to set it.
    fwd = request.headers.get("X-Forwarded-For", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")
    return f"{scope}:{ip}"


class RateLimiter:
    """FastAPI dependency: `Depends(RateLimiter("login", 5, 60))`."""

    def __init__(self, scope: str, limit: int, window_s: int):
        self.scope, self.limit, self.window_s = scope, limit, window_s

    async def __call__(self, request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        now = time.monotonic()
        key = _client_key(request, self.scope)
        recent = [t for t in _hits[key] if now - t < self.window_s]
        if len(recent) >= self.limit:
            retry = int(self.window_s - (now - recent[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Try again in {retry}s.",
                headers={"Retry-After": str(retry)},
            )
        recent.append(now)
        _hits[key] = recent
        if len(_hits) > _MAX_TRACKED:          # bound memory against IP spraying
            for k in [k for k, v in _hits.items() if not v or now - v[-1] > self.window_s]:
                _hits.pop(k, None)


def reset() -> None:
    """Test hook — clears all windows."""
    _hits.clear()
