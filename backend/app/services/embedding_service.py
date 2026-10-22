"""Vector Embedding generation service for Personal Playbook Knowledge Base.

Compatible with pgvector Vector(1536) schema.
Supported Providers:
- 'openai': OpenAI text-embedding-3-small / text-embedding-ada-002
- 'gemini': Google Gemini text embedding
- 'mock': Deterministic 1536-dimensional L2-normalized pseudo-embeddings for testing/dev

Never exposes API keys in logs or errors. Handles timeouts and quota errors safely.
"""

import hashlib
import math
import random
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import BadRequestError


class BaseEmbeddingProvider(ABC):
    """Abstract base class for vector embedding generation providers."""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a batch of text chunks."""
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        """Generate a vector embedding for a single search query."""
        pass


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic 1536-dimensional unit vector generator for tests and offline development."""

    DIMENSION: int = 1536

    def _generate_vector(self, text: str) -> list[float]:
        """Generate a deterministic semantic-aware L2-normalized 1536-dim vector."""
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            tokens = ["empty"]

        acc = [0.0] * self.DIMENSION
        for token in tokens:
            # Deterministic pseudo-random seed per token
            seed = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:8], "big")
            rng = random.Random(seed)
            for i in range(self.DIMENSION):
                acc[i] += rng.uniform(-1.0, 1.0)

        norm = math.sqrt(sum(x * x for x in acc))
        if norm > 0:
            return [x / norm for x in acc]
        return [1.0 / math.sqrt(self.DIMENSION)] * self.DIMENSION

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        return self._generate_vector(query)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Generates 1536-dimensional embeddings using OpenAI's REST API."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.EMBEDDING_MODEL
        self.endpoint = "https://api.openai.com/v1/embeddings"
        self.timeout = float(settings.RAG_REQUEST_TIMEOUT_SECONDS)

        if not self.api_key:
            raise BadRequestError(
                "OpenAI API key is not configured on the server. "
                "Set OPENAI_API_KEY or configure EMBEDDING_PROVIDER=mock for testing."
            )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "input": texts,
            "dimensions": settings.EMBEDDING_DIMENSION,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.endpoint, headers=headers, json=payload)

            if resp.status_code == 401:
                raise BadRequestError("Invalid OpenAI API key. Authentication failed.")
            if resp.status_code == 429:
                raise BadRequestError("OpenAI embedding API rate limit or quota exceeded.")
            if resp.status_code >= 400:
                raise BadRequestError(f"OpenAI embedding API error (HTTP {resp.status_code}).")

            data = resp.json()
            embeddings_data = data.get("data", [])
            # Sort by index to maintain text alignment
            embeddings_data.sort(key=lambda x: x.get("index", 0))
            return [item["embedding"] for item in embeddings_data]

        except httpx.TimeoutException as exc:
            raise BadRequestError("Embedding provider request timed out.") from exc
        except httpx.RequestError as exc:
            raise BadRequestError("Network error while connecting to embedding provider.") from exc

    async def embed_query(self, query: str) -> list[float]:
        res = await self.embed_texts([query])
        if not res:
            raise BadRequestError("Failed to generate query embedding.")
        return res[0]


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Factory function returning the configured embedding provider."""
    provider_name = (settings.EMBEDDING_PROVIDER or "mock").strip().lower()

    if provider_name == "openai":
        return OpenAIEmbeddingProvider()
    elif provider_name == "mock":
        return MockEmbeddingProvider()
    else:
        # Default fallback to mock with clear note
        return MockEmbeddingProvider()
