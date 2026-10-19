"""Configurable LLM client.

Supported providers (all hosted providers speak the OpenAI Chat Completions
protocol, so a single request builder is used):

* ``none`` — extractive answers only; the platform stays fully usable.
* ``gemini`` — Google Gemini via its official OpenAI-compatible endpoint.
* ``groq`` — Groq Cloud (fast open-weight models).
* ``openrouter`` — OpenRouter (including free models).
* ``openai`` — OpenAI or any custom OpenAI-compatible base URL.
* ``openai_compatible`` — explicit custom endpoint (needs LLM_BASE_URL).
* ``ollama`` — local Ollama server.

Secrets are never logged. When a provider is configured but unreachable, the
failure is recorded on ``LLMClient.last_error`` (key redacted) so callers can
disclose *why* they fell back to extractive answers instead of silently
pretending the model answered.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..config import settings


@dataclass(frozen=True)
class ProviderPreset:
    name: str
    label: str
    base_url: str
    default_model: str
    key_env: str


PROVIDER_PRESETS: dict[str, ProviderPreset] = {
    "openai": ProviderPreset(
        "openai", "OpenAI", "https://api.openai.com/v1", "gpt-4o-mini", "OPENAI_API_KEY"
    ),
    "gemini": ProviderPreset(
        "gemini",
        "Google Gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-3.5-flash-lite",
        "GEMINI_API_KEY",
    ),
    "groq": ProviderPreset(
        "groq", "Groq", "https://api.groq.com/openai/v1", "openai/gpt-oss-20b", "GROQ_API_KEY"
    ),
    "openrouter": ProviderPreset(
        "openrouter",
        "OpenRouter",
        "https://openrouter.ai/api/v1",
        "meta-llama/llama-3.2-3b-instruct:free",
        "OPENROUTER_API_KEY",
    ),
    "openai_compatible": ProviderPreset(
        "openai_compatible",
        "Custom OpenAI-compatible endpoint",
        "",
        "",
        "LLM_API_KEY",
    ),
    "ollama": ProviderPreset("ollama", "Ollama (local)", "", "", ""),
}

SUPPORTED_PROVIDERS = ("none", *PROVIDER_PRESETS)


@dataclass
class LLMStatus:
    provider: str
    configured: bool
    model: str
    detail: str
    base_url: str = ""


@dataclass
class ProviderConfig:
    provider: str
    configured: bool
    model: str
    base_url: str
    api_key: str
    detail: str

    def status(self) -> LLMStatus:
        return LLMStatus(
            provider=self.provider,
            configured=self.configured,
            model=self.model,
            detail=self.detail,
            base_url=self.base_url,
        )


def _provider_key(provider: str) -> str:
    if provider == "openai":
        return (settings.openai_api_key or "").strip()
    return (getattr(settings, f"{provider}_api_key", "") or "").strip()


def resolve_provider(provider: str | None = None) -> ProviderConfig:
    """Resolve the configured provider, its endpoint, model and key."""
    raw = (provider or settings.llm_provider or "none").strip().lower()
    if raw in {"", "none", "disabled", "off"}:
        return ProviderConfig(
            provider="none",
            configured=False,
            model="",
            base_url="",
            api_key="",
            detail=(
                "No generative provider configured. Answers are composed from retrieved "
                "official evidence only (extractive mode)."
            ),
        )

    preset = PROVIDER_PRESETS.get(raw)
    if preset is None:
        return ProviderConfig(
            provider=raw,
            configured=False,
            model="",
            base_url="",
            api_key="",
            detail=(
                f"Unknown LLM_PROVIDER '{raw}'. Supported values: "
                + ", ".join(SUPPORTED_PROVIDERS)
                + "."
            ),
        )

    model = (settings.llm_model or "").strip() or preset.default_model

    if raw == "ollama":
        base_url = (settings.ollama_base_url or "").strip()
        if not model:
            return ProviderConfig(
                provider=raw,
                configured=False,
                model="",
                base_url=base_url,
                api_key="",
                detail=(
                    "LLM_PROVIDER=ollama but LLM_MODEL is not set. Set LLM_MODEL to an "
                    "installed Ollama model (for example llama3.2:3b)."
                ),
            )
        return ProviderConfig(
            provider=raw,
            configured=True,
            model=model,
            base_url=base_url,
            api_key="",
            detail=(
                f"Ollama endpoint {base_url} (model {model}); availability is checked at "
                "request time. Local inference needs enough RAM (typically 8 GB+)."
            ),
        )

    if raw == "openai":
        base_url = (settings.llm_base_url or settings.openai_base_url or "").strip()
    else:
        base_url = (settings.llm_base_url or preset.base_url).strip()
    base_url = base_url.rstrip("/")

    api_key = (settings.llm_api_key or "").strip() or _provider_key(raw)

    if raw == "openai_compatible":
        missing = []
        if not base_url:
            missing.append("LLM_BASE_URL")
        if not model:
            missing.append("LLM_MODEL")
        if not api_key:
            missing.append("LLM_API_KEY")
        if missing:
            return ProviderConfig(
                provider=raw,
                configured=False,
                model=model,
                base_url=base_url,
                api_key="",
                detail=(
                    "LLM_PROVIDER=openai_compatible requires "
                    + ", ".join(missing)
                    + " to be set."
                ),
            )
    elif not api_key:
        return ProviderConfig(
            provider=raw,
            configured=False,
            model=model,
            base_url=base_url,
            api_key="",
            detail=(
                f"LLM_PROVIDER={raw} but {preset.key_env} (or LLM_API_KEY) is not set. "
                "Falling back to retrieval-only answers."
            ),
        )

    return ProviderConfig(
        provider=raw,
        configured=True,
        model=model,
        base_url=base_url,
        api_key=api_key,
        detail=f"{preset.label} configured at {base_url} (model {model}).",
    )


def llm_status() -> LLMStatus:
    return resolve_provider().status()


def _redact(text: str, secret: str) -> str:
    if secret:
        text = text.replace(secret, "[redacted]")
    return text


def _safe_error(exc: Exception, api_key: str) -> str:
    """Return a short, secret-free description of a provider failure."""
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        status = response.status_code if response is not None else "?"
        detail = ""
        if response is not None:
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    error = payload.get("error")
                    if isinstance(error, dict):
                        detail = str(error.get("message") or "")
                    elif error:
                        detail = str(error)
                    elif payload.get("message"):
                        detail = str(payload["message"])
            except Exception:  # noqa: BLE001 - body may not be JSON
                detail = response.text or ""
        detail = " ".join(detail.split())[:300]
        message = f"HTTP {status} from provider"
        if detail:
            message += f": {detail}"
    else:
        message = f"{type(exc).__name__}: {exc}"
        message = " ".join(message.split())[:400]
    return _redact(message, api_key)


class LLMClient:
    def __init__(self, config: ProviderConfig | str) -> None:
        if isinstance(config, str):
            config = resolve_provider(config)
        self.config = config
        self.provider = config.provider
        self.model = config.model
        self.base_url = config.base_url
        self.api_key = config.api_key
        self.last_error: str | None = None

    def available(self) -> bool:
        if self.provider == "ollama":
            try:
                httpx.get(f"{self.base_url.rstrip('/')}/api/tags", timeout=3.0)
                return True
            except Exception:  # noqa: BLE001
                return False
        return bool(self.api_key and self.base_url)

    def generate(self, system_prompt: str, user_prompt: str, *, max_tokens: int = 700) -> str | None:
        self.last_error = None
        if not self.available():
            self.last_error = (
                f"{self.provider} endpoint is not reachable at {self.base_url}"
                if self.provider == "ollama"
                else f"{self.provider} is missing an API key or base URL"
            )
            return None
        if self.provider == "ollama":
            return self._ollama(system_prompt, user_prompt, max_tokens)
        return self._chat_completions(system_prompt, user_prompt, max_tokens)

    def check(self) -> tuple[bool, str]:
        """Make a minimal live call so operators can verify credentials."""
        if not self.available():
            return False, self.last_error or f"{self.provider} is not reachable."
        reply = self.generate(
            "You are a connectivity check. Follow the instruction exactly.",
            "Reply with exactly: OK",
            max_tokens=16,
        )
        if reply:
            return True, f"{self.provider} responded: {reply[:80]}"
        return False, self.last_error or "The provider returned no content."

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/maseedwasimullah-crypto/mahsud-guide"
            headers["X-Title"] = settings.app_name
        return headers

    def _chat_completions(
        self, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> str | None:
        try:
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": settings.llm_temperature,
                },
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                self.last_error = "The provider response contained no choices."
                return None
            content = (choices[0].get("message") or {}).get("content")
            if isinstance(content, list):
                content = "".join(
                    str(part.get("text", "")) for part in content if isinstance(part, dict)
                )
            text = (content or "").strip()
            if not text:
                self.last_error = "The provider returned an empty message."
                return None
            return text
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            self.last_error = _safe_error(exc, self.api_key)
            return None

    def _ollama(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str | None:
        try:
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "options": {
                        "temperature": settings.llm_temperature,
                        "num_predict": max_tokens,
                    },
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=max(settings.llm_timeout_seconds, 180.0),
            )
            response.raise_for_status()
            text = (response.json().get("message") or {}).get("content", "").strip()
            if not text:
                self.last_error = "Ollama returned an empty message."
                return None
            return text
        except Exception as exc:  # noqa: BLE001
            self.last_error = _safe_error(exc, "")
            return None


def get_llm() -> LLMClient | None:
    config = resolve_provider()
    if not config.configured:
        return None
    return LLMClient(config)
