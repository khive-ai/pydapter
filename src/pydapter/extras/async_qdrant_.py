"""
AsyncQdrantAdapter - vector upsert / search using AsyncQdrantClient.
"""

from __future__ import annotations

from typing import Sequence, TypeVar

from pydantic import BaseModel
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qd

from ..async_core import AsyncAdapter

T = TypeVar("T", bound=BaseModel)


class AsyncQdrantAdapter(AsyncAdapter[T]):
    obj_key = "async_qdrant"

    @staticmethod
    def _client(url: str | None):
        return AsyncQdrantClient(url=url) if url else AsyncQdrantClient(":memory:")

    # outgoing
    @classmethod
    async def to_obj(
        cls,
        subj: T | Sequence[T],
        /,
        *,
        collection,
        vector_field="embedding",
        id_field="id",
        url=None,
        **kw,
    ):
        items = subj if isinstance(subj, Sequence) else [subj]
        dim = len(getattr(items[0], vector_field))
        client = cls._client(url)
        await client.recreate_collection(
            collection,
            vectors_config=qd.VectorParams(size=dim, distance="Cosine"),
        )
        points = [
            qd.PointStruct(
                id=getattr(i, id_field),
                vector=getattr(i, vector_field),
                payload=i.model_dump(exclude={vector_field}),
            )
            for i in items
        ]
        await client.upsert(collection, points)

    # incoming
    @classmethod
    async def from_obj(cls, subj_cls: type[T], obj: dict, /, *, many=True, **kw):
        client = cls._client(obj.get("url"))
        res = await client.search(
            obj["collection"],
            obj["query_vector"],
            limit=obj.get("top_k", 5),
            with_payload=True,
        )
        docs = [r.payload for r in res]
        return (
            [subj_cls.model_validate(d) for d in docs]
            if many
            else subj_cls.model_validate(docs[0])
        )
