"""Provider selection, request shaping and failure transparency for the LLM client."""

from __future__ import annotations

import httpx
import pytest

from app.config import settings
from app.services import llm

CLEAN_FIELDS = {
    "llm_provider": "none",
    "llm_model": "",
    "llm_api_key": "",
    "llm_base_url": "",
    "llm_temperature": 0.1,
    "llm_timeout_seconds": 90.0,
    "openai_api_key": "",
    "openai_base_url": "https://api.openai.com/v1",
    "gemini_api_key": "",
    "groq_api_key": "",
    "openrouter_api_key": "",
    "ollama_base_url": "http://localhost:11434",
}


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch):
    for field, value in CLEAN_FIELDS.items():
        monkeypatch.setattr(settings, field, value)
    yield


@pytest.mark.parametrize(
    ("provider", "key_field", "base_url", "model"),
    [
        ("gemini", "gemini_api_key", "https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash"),
        ("groq", "groq_api_key", "https://api.groq.com/openai/v1", "openai/gpt-oss-20b"),
        ("openrouter", "openrouter_api_key", "https://openrouter.ai/api/v1", "meta-llama/llama-3.2-3b-instruct:free"),
        ("openai", "openai_api_key", "https://api.openai.com/v1", "gpt-4o-mini"),
    ],
)
def test_provider_presets(monkeypatch, provider, key_field, base_url, model):
    monkeypatch.setattr(settings, "llm_provider", provider)
    monkeypatch.setattr(settings, key_field, "test-key")
    status = llm.llm_status()
    assert status.configured is True
    assert status.provider == provider
    assert status.base_url.rstrip("/") == base_url.rstrip("/")
    assert status.model == model


def test_missing_key_is_reported_not_faked():
    settings.llm_provider = "gemini"
    status = llm.llm_status()
    assert status.configured is False
    assert "GEMINI_API_KEY" in status.detail
    assert llm.get_llm() is None


def test_unknown_provider_is_rejected_with_hint():
    settings.llm_provider = "chatgpt"
    status = llm.llm_status()
    assert status.configured is False
    assert "Unknown LLM_PROVIDER" in status.detail
    assert "gemini" in status.detail


def test_generic_key_takes_precedence(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.setattr(settings, "llm_api_key", "generic-key")
    client = llm.get_llm()
    assert client is not None
    assert client.api_key == "generic-key"


def test_openai_compatible_requires_endpoint_and_model():
    settings.llm_provider = "openai_compatible"
    settings.llm_api_key = "key"
    status = llm.llm_status()
    assert status.configured is False
    assert "LLM_BASE_URL" in status.detail and "LLM_MODEL" in status.detail

    settings.llm_base_url = "https://example.test/v1"
    settings.llm_model = "my-model"
    assert llm.llm_status().configured is True


def test_ollama_requires_a_model_name():
    settings.llm_provider = "ollama"
    status = llm.llm_status()
    assert status.configured is False
    assert "LLM_MODEL" in status.detail
    settings.llm_model = "llama3.2:3b"
    assert llm.llm_status().configured is True


def test_generation_uses_provider_endpoint_and_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "secret-key")
    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "  grounded answer  "}}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        captured["json"] = kwargs.get("json")
        return FakeResponse()

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    client = llm.get_llm()
    assert client is not None
    assert client.generate("system", "user") == "grounded answer"
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["json"]["model"] == "openai/gpt-oss-20b"
    assert captured["headers"]["Authorization"] == "Bearer secret-key"


def test_failure_records_sanitized_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "super-secret-key")
    request = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
    response = httpx.Response(
        401,
        request=request,
        json={"error": {"message": "API key not valid: super-secret-key"}},
    )

    def fake_post(*_args, **_kwargs):
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    client = llm.get_llm()
    assert client is not None
    assert client.generate("system", "user") is None
    assert client.last_error is not None
    assert "401" in client.last_error
    assert "super-secret-key" not in client.last_error


def test_chat_discloses_provider_failure_instead_of_silently_falling_back(monkeypatch, client):
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "super-secret-key")

    def fake_post(*_args, **_kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    body = client.post(
        "/api/assistant/chat",
        json={"message": "What is the aggregate formula for MBBS?", "program": "MBBS"},
    ).json()
    assert body["provider_configured"] is True
    assert body["generated_by"] == "extractive"
    assert body["provider_error"]
    assert "super-secret-key" not in body["provider_error"]
    assert any("could not be reached" in d for d in body["disclaimers"])
