"""Shared normalization and parsing helpers for backend agents."""

import json
import re
from typing import Any, List, Optional


def safe_float(value: object, default: float = 0.0) -> float:
    """Convert a value to float safely, returning a default on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def dedupe_preserve_order(items: List[str]) -> List[str]:
    """Remove duplicates while preserving original order and non-empty values."""
    seen = set()
    ordered = []
    for item in items:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def normalize_phrase_list(items: object, limit: int = 5) -> List[str]:
    """Normalize a list of short phrases into a clean bounded list."""
    if not isinstance(items, list):
        return []

    phrases = []
    for item in items:
        text = sanitize_llm_text(str(item)).strip(" -\n\t")
        if text:
            phrases.append(text)
    return dedupe_preserve_order(phrases)[:limit]


def normalize_short_text(value: object, fallback: str = "Unavailable") -> str:
    """Normalize a short text field with a fallback for empty outputs."""
    text = sanitize_llm_text(str(value or "")).strip()
    return text or fallback


def sanitize_llm_text(text: str) -> str:
    """Strip meta-output, code fences, and excess whitespace from model text."""
    cleaned = text or ""
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"```(?:json|markdown|md)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "")
    cleaned = re.sub(
        r"^\s*(the user wants me to|the user asked me to|i will|i should|i need to)\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_json_payload(text: str) -> Optional[dict]:
    """Parse a dict-shaped JSON payload from raw LLM output."""
    cleaned = sanitize_llm_text(text)
    if not cleaned:
        return None

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def model_to_dict(model: Any) -> dict:
    """Convert a Pydantic model-like object into a standard dict."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


__all__ = [
    "dedupe_preserve_order",
    "extract_json_payload",
    "model_to_dict",
    "normalize_phrase_list",
    "normalize_short_text",
    "safe_float",
    "sanitize_llm_text",
]
