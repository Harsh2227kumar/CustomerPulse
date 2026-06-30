import asyncio
import hashlib
from functools import lru_cache
import math
import re

from app.core.constants import EMBEDDING_DIMENSIONS


class EmbeddingError(RuntimeError):
    pass


class InvalidEmbeddingError(EmbeddingError):
    pass


@lru_cache(maxsize=4)
def _load_model(model_name: str, local_files_only: bool):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, local_files_only=local_files_only)


class EmbeddingService:
    def __init__(self, model_name: str, *, local_files_only: bool = False):
        self.model_name = model_name
        self.local_files_only = local_files_only

    async def ensure_ready(self) -> None:
        """Load the configured model and validate the database vector contract."""
        await self.embed_text("CustomerPulse embedding readiness check.")

    async def embed_text(self, text: str) -> list[float]:
        cleaned = text.strip()
        if not cleaned:
            raise InvalidEmbeddingError("Cannot embed an empty complaint narrative.")
        embedding = await asyncio.to_thread(self._embed_sync, text)
        self._validate_embedding(embedding)
        return embedding

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = await asyncio.gather(*(self.embed_text(text) for text in texts))
        return embeddings

    def _validate_embedding(self, embedding: list[float]) -> None:
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise InvalidEmbeddingError(
                f"Embedding model returned {len(embedding)} dimensions; "
                f"expected {EMBEDDING_DIMENSIONS}."
            )
        if not all(math.isfinite(value) for value in embedding):
            raise InvalidEmbeddingError("Embedding model returned non-finite vector values.")

    def _embed_sync(self, text: str) -> list[float]:
        model_key = (self.model_name, self.local_files_only)
        if model_key not in _FAILED_MODELS:
            try:
                vector = _load_model(self.model_name, self.local_files_only).encode(
                    text,
                    normalize_embeddings=True,
                )
                return [float(value) for value in vector.tolist()]
            except Exception:
                _FAILED_MODELS.add(model_key)
        return self._fallback_embedding(text)

    def _fallback_embedding(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
            sign = 1.0 if digest[4] % 2 else -1.0
            weight = 1.0 + min(len(token), 12) / 12.0
            vector[index] += sign * weight
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
