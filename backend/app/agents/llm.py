"""Shared LLM client and fallback helpers for backend agents."""

import os
from typing import Optional, Type

from langchain_openai import ChatOpenAI
from pydantic import BaseModel


DEFAULT_BASE_URL = os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
DEFAULT_PRIMARY_MODEL = os.environ.get("MINIMAX_PRIMARY_MODEL", "MiniMax-M2.7")
DEFAULT_FALLBACK_MODELS = [
    model.strip()
    for model in os.environ.get(
        "MINIMAX_FALLBACK_MODELS",
        "MiniMax-M2.7-highspeed,MiniMax-M2.5,MiniMax-M2.5-highspeed",
    ).split(",")
    if model.strip()
]


def get_model_candidates() -> list[str]:
    """Return the ordered MiniMax model list used for fallback invocation."""
    models = [DEFAULT_PRIMARY_MODEL, *DEFAULT_FALLBACK_MODELS]
    deduped = []
    for model in models:
        if model and model not in deduped:
            deduped.append(model)
    return deduped


def create_llm(model_name: str, structured_schema: Optional[Type[BaseModel]] = None):
    """Create a MiniMax-backed chat client with optional structured output."""
    api_key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not api_key or api_key == "your_minimax_api_key_here":
        raise RuntimeError("MINIMAX_API_KEY is missing or invalid.")

    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=os.environ.get("MINIMAX_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL,
        temperature=0.2,
    )
    if structured_schema is not None:
        return llm.with_structured_output(structured_schema)
    return llm


def is_rate_limit_error(exc: Exception) -> bool:
    """Detect MiniMax rate-limit failures from exception text."""
    message = str(exc).lower()
    return "rate limit" in message or "rate_limit_exceeded" in message or "error code: 429" in message


def invoke_with_model_fallback(messages, structured_schema: Optional[Type[BaseModel]] = None):
    """Invoke the configured MiniMax models in fallback order."""
    last_exception = None

    for model_name in get_model_candidates():
        try:
            llm = create_llm(model_name, structured_schema=structured_schema)
            return llm.invoke(messages)
        except Exception as exc:
            last_exception = exc
            if not is_rate_limit_error(exc):
                raise

    if last_exception is not None:
        raise last_exception
    raise RuntimeError("No MiniMax model candidates were configured.")


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_FALLBACK_MODELS",
    "DEFAULT_PRIMARY_MODEL",
    "create_llm",
    "get_model_candidates",
    "invoke_with_model_fallback",
    "is_rate_limit_error",
]
