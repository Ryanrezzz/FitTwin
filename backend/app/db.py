"""MongoDB connection + Beanie initialization.

The only module (besides repositories) that talks to Motor/Beanie. `init_db` is
resilient: a missing or unreachable Mongo logs a warning and leaves the app up in
"degraded" mode (agent core + health still work; auth/profile routes 503) rather
than crashing startup. This preserves the project's run-fully-offline property.
"""
from __future__ import annotations

import logging

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.config import settings
from app.models import ALL_MODELS

log = logging.getLogger(__name__)

# Beanie 2.x uses PyMongo's native async driver (AsyncMongoClient), not Motor.
_client: AsyncMongoClient | None = None
_ready = False


async def init_db() -> bool:
    """Connect + init Beanie. Returns True on success, False if Mongo is unreachable."""
    global _client, _ready
    try:
        _client = AsyncMongoClient(
            settings.mongo_uri, serverSelectionTimeoutMS=settings.mongo_timeout_ms
        )
        await _client.admin.command("ping")
        await init_beanie(database=_client[settings.mongo_db], document_models=ALL_MODELS)
        _ready = True
        log.info("MongoDB connected (db=%s)", settings.mongo_db)
    except Exception as e:  # noqa: BLE001 — degrade gracefully instead of crashing
        _ready = False
        log.warning("MongoDB unavailable (%s); running without persistence", e)
    return _ready


async def close_db() -> None:
    global _client, _ready
    if _client is not None:
        await _client.close()
    _client = None
    _ready = False


def db_ready() -> bool:
    return _ready
