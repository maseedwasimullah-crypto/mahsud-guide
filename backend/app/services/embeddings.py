"""Embedding providers.

``local`` is a deterministic hashing embedder that needs no API key and no model
download, so the platform is fully usable offline. ``openai`` is optional and
used only when an API key is configured. Providers are interchangeable behind
``embed_texts``.
"""

from __future__ import annotations

import hashlib
import math
import re

import httpx

from ..config import settings

TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _local_embed(text: str, dim: int) -> list[float]:
    vector = [0.0] * dim
    tokens = _tokenize(text)
    if not tokens:
        return vector
    for position, token in enumerate(tokens):
        h = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(h[:4], "big") % dim
        sign = 1.0 if h[4] % 2 == 0 else -1.0
        vector[idx] += sign * (1.0 + min(len(token), 12) / 12.0)
        # bigram signal for a little word-order sensitivity
        if position:
            bigram = f"{tokens[position - 1]} {token}"
            hb = hashlib.blake2b(bigram.encode("utf-8"), digest_size=8).digest()
            ib = int.from_bytes(hb[:4], "big") % dim
            sb = 1.0 if hb[4] % 2 == 0 else -1.0
            vector[ib] += sb * 0.5
    norm = math.sqrt(sum(v * v for v in vector))
    if norm:
        vector = [v / norm for v in vector]
    return vector


def _openai_embed(texts: list[str]) -> list[list[float]]:
    response = httpx.post(
        f"{settings.openai_base_url.rstrip('/')}/embeddings",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={"model": settings.embedding_model, "input": texts},
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()["data"]
    return [item["embedding"] for item in sorted(data, key=lambda d: d["index"])]


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if settings.embedding_provider == "openai" and settings.openai_api_key:
        try:
            return _openai_embed(texts)
        except Exception:  # noqa: BLE001 - fall back rather than break the app
            pass
    return [_local_embed(t, settings.embedding_dim) for t in texts]


def embed_query(text: str) -> tuple[list[float], str]:
    provider = settings.embedding_provider if (
        settings.embedding_provider == "openai" and settings.openai_api_key
    ) else "local"
    return embed_texts([text])[0], provider


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
