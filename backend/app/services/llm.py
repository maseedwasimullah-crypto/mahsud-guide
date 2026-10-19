"""Configurable LLM client.

The platform must stay usable when no paid provider is configured, so
``get_llm()`` may legitimately return ``None``. Callers must handle that case
with a deterministic, retrieval-grounded fallback.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..config import settings


@dataclass
class LLMStatus:
    provider: str
    configured: bool
    model: str
    detail: str


def llm_status() -> LLMStatus:
    provider = (settings.llm_provider or "none").lower()
    if provider == "openai":
        if settings.openai_api_key:
            return LLMStatus("openai", True, settings.llm_model, "OpenAI-compatible endpoint configured.")
        return LLMStatus(
            "openai", False, settings.llm_model,
            "LLM_PROVIDER=openai but OPENAI_API_KEY is not set. Falling back to retrieval-only answers.",
        )
    if provider == "ollama":
        return LLMStatus(
            "ollama", True, settings.llm_model,
            f"Ollama endpoint {settings.ollama_base_url} (availability is checked at request time).",
        )
    return LLMStatus(
        "none", False, "",
        "No generative provider configured. Answers are composed from retrieved official "
        "evidence only (extractive mode).",
    )


class LLMClient:
    def __init__(self, provider: str) -> None:
        self.provider = provider

    def available(self) -> bool:
        if self.provider == "openai":
            return bool(settings.openai_api_key)
        if self.provider == "ollama":
            try:
                httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=3.0)
                return True
            except Exception:  # noqa: BLE001
                return False
        return False

    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 700) -> str | None:
        if self.provider == "openai" and settings.openai_api_key:
            return self._openai(system_prompt, user_prompt, max_tokens)
        if self.provider == "ollama":
            return self._ollama(system_prompt, user_prompt, max_tokens)
        return None

    def _openai(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str | None:
        try:
            response = httpx.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.1,
                },
                timeout=90.0,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception:  # noqa: BLE001 - degrade gracefully
            return None

    def _ollama(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str | None:
        try:
            response = httpx.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                json={
                    "model": settings.llm_model,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": max_tokens},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=180.0,
            )
            response.raise_for_status()
            return response.json()["message"]["content"].strip()
        except Exception:  # noqa: BLE001
            return None


def get_llm() -> LLMClient | None:
    provider = (settings.llm_provider or "none").lower()
    if provider in {"openai", "ollama"}:
        return LLMClient(provider)
    return None
