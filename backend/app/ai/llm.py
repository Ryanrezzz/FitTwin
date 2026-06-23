"""Provider-agnostic LLM adapter.

Design goals:
- Swap Gemini / OpenAI / Ollama via one env var (LLM_PROVIDER).
- The agent core must run with NO provider installed and NO API key: the "fake"
  provider (and every real provider on error) returns the caller's deterministic
  `fallback`. This is the circuit-breaker from the design docs — the LLM only
  ever *enriches* a result the agent already computed; it can never break it.
"""
from __future__ import annotations

import logging
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.config import settings

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    name: str

    def structured(self, *, system: str, user: str, schema: type[T], fallback: T) -> T: ...

    def text(self, *, system: str, user: str, fallback: str = "") -> str: ...


class FakeProvider:
    """Deterministic, offline. Returns the caller's fallback verbatim."""

    name = "fake"

    def structured(self, *, system: str, user: str, schema: type[T], fallback: T) -> T:
        return fallback

    def text(self, *, system: str, user: str, fallback: str = "") -> str:
        return fallback


class _LangChainProvider:
    """Wraps any LangChain chat model; degrades to fallback on any failure."""

    def __init__(self, model, name: str):
        self._model = model
        self.name = name

    def structured(self, *, system: str, user: str, schema: type[T], fallback: T) -> T:
        try:
            out = self._model.with_structured_output(schema).invoke(
                [("system", system), ("human", user)]
            )
            return out if isinstance(out, schema) else schema.model_validate(out)
        except Exception as e:  # noqa: BLE001 — circuit breaker is intentional
            log.warning("LLM structured call failed (%s); using deterministic fallback", e)
            return fallback

    def text(self, *, system: str, user: str, fallback: str = "") -> str:
        try:
            resp = self._model.invoke([("system", system), ("human", user)])
            return getattr(resp, "content", None) or fallback
        except Exception as e:  # noqa: BLE001
            log.warning("LLM text call failed (%s); using deterministic fallback", e)
            return fallback


def _build_gemini() -> LLMProvider:
    from langchain_google_genai import ChatGoogleGenerativeAI

    model = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.gemini_api_key,
        temperature=settings.llm_temperature,
    )
    return _LangChainProvider(model, "gemini")


def _build_openai() -> LLMProvider:
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=settings.llm_temperature,
    )
    return _LangChainProvider(model, "openai")


def _build_ollama() -> LLMProvider:
    from langchain_ollama import ChatOllama

    model = ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=settings.llm_temperature,
    )
    return _LangChainProvider(model, "ollama")


_BUILDERS = {"gemini": _build_gemini, "openai": _build_openai, "ollama": _build_ollama}
_cache: LLMProvider | None = None


def get_llm() -> LLMProvider:
    """Singleton accessor. Falls back to FakeProvider if the provider can't init."""
    global _cache
    if _cache is not None:
        return _cache
    provider = settings.llm_provider.lower()
    if provider == "fake":
        _cache = FakeProvider()
        return _cache
    builder = _BUILDERS.get(provider)
    if builder is None:
        log.warning("Unknown LLM_PROVIDER=%r; using fake", provider)
        _cache = FakeProvider()
        return _cache
    try:
        _cache = builder()
    except Exception as e:  # noqa: BLE001 — missing SDK or bad config -> stay alive
        log.warning("Could not init provider %r (%s); using fake", provider, e)
        _cache = FakeProvider()
    return _cache


def reset_llm_cache() -> None:
    """Test hook."""
    global _cache
    _cache = None
