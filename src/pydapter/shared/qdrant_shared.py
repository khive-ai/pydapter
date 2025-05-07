# qdrant_shared.py
from functools import lru_cache
from qdrant_client import QdrantClient
from qdrant_client.async_qdrant_client import AsyncQdrantClient


@lru_cache(maxsize=1)
def get_sync_client(url: str | None = None) -> QdrantClient:
    return QdrantClient(url=url) if url else QdrantClient(":memory:")


@lru_cache(maxsize=1)
def get_async_client(url: str | None = None) -> AsyncQdrantClient:
    return AsyncQdrantClient(url=url) if url else AsyncQdrantClient(":memory:")
